from os import listdir
import subprocess
from subprocess import check_output, CalledProcessError
from os.path import isfile, join
import configparser
import tempfile
import json
import argparse
import copy
import re
import os
import sys
from itertools import chain


def to_nix(input: str) -> str:
    output = ""
    with tempfile.NamedTemporaryFile(mode="w") as tf:
        tf.write(json.dumps(input))
        tf.flush()
        output = check_output(
            [
                "nix-instantiate",
                "--expr",
                "--eval",
                f'builtins.fromJSON (builtins.readFile "{tf.name}")',
            ],
            text=True,
        )
    return output


def format(input: str) -> str:
    return check_output(
        [
            "nix",
            "--extra-experimental-features",
            "nix-command flakes",
            "run",
            "nixpkgs#nixfmt-rfc-style",
        ],
        text=True,
        input=input,
    )


PATHS = [
    "/run/NetworkManager/system-connections",
    "/etc/NetworkManager/system-connections",
]

NMSUFFIX = ".nmconnection"
# matchSetting apparently does not map directly onto the top level key (from, to) or just val if both are the same
# same goes for matchType
PWEXTRACTIONS = [
    {
        "matchType": ("wifi", "802-11-wireless"),
        "matchSetting": ("wifi-security", "802-11-wireless-security"),
        "key": "psk",
    },
    {
        "matchType": "wifi",
        "matchSetting": "802-1x",
        "key": "password",
    },
    {
        "matchType": "wifi",
        "matchSetting": "802-1x",
        "key": "identity",
    },
    {
        "matchType": "wireguard",
        "matchSetting": "wireguard",
        "key": "private-key",
    },
]


def normalize_dict(e) -> dict:
    matchSetting = e["matchSetting"]
    matchType = e["matchType"]
    if not isinstance(matchSetting, tuple):
        matchSetting = (matchSetting, matchSetting)
    if not isinstance(matchType, tuple):
        matchType = (matchType, matchType)
    return {"key": e["key"], "matchSetting": matchSetting, "matchType": matchType}


# normalizing these extractions
PWEXTRACTIONS = map(normalize_dict, PWEXTRACTIONS)
PWEXTRACTIONS = list(PWEXTRACTIONS)

DELIMITER = "============================="

parser = argparse.ArgumentParser(
    prog="nm2nix",
    description="Converts .nmconnection files into nix code",
)

parser.add_argument(
    "-cd", help=f"wether to cd to { ", ".join(PATHS)}", action="store_true"
)
parser.add_argument(
    "-s", help="wether to split output to one file each", action="store_true"
)
parser.add_argument(
    "-f", help="wether to format the files / output", action="store_true"
)
parser.add_argument(
    "-e", help="file names of connections to exclude", action="append", default=[]
)

parser.add_argument(
    "-pwfolder",
    help="if given, write passwords to a secret file inside this folder, using nm-file-secret-agent to subsitute them back",
)

parser.add_argument(
    "-use-agenix",
    help="wether to use agenix to obtain secrets inside of the secret files",
    action="store_true",
)

parser.add_argument(
    "-secrets-nix-path",
    help="path to secrets.nix to use",
)

parser.add_argument(
    "-interactive-retry-agenix",
    help="wether to retry agenix encryption after an error having recieve a ENTER",
    action="store_true",
)

parser.add_argument(
    "-agenix-continue-on-err",
    help="wether to continue when agenix threw an erro",
    action="store_true",
)

parser.add_argument(
    "-output-missing-keys",
    action="store_true",
)

parser.add_argument(
    "agenix_extra_args",
    help="extra args passed to agenix. given as one string",
    nargs="*",
)

args = parser.parse_args()


# returns file path where the secret should be written to
def target_file_path(base_folder: str, connection_name, match_type, match_setting, key):
    return f"{base_folder}/{connection_name}-{match_type}-{match_setting}-{key}"


def target_nix_secret_file_path(
    base_folder, connection_name, match_type, match_setting, key
):
    return f"{base_folder}/{connection_name}-{match_type}-{match_setting}-{key}.nix"


def subsitute_file_path_expr(
    base_folder: str, connection_name, match_type, match_setting, key, target_file_path
):
    if args.use_agenix:
        return f"AGENIXKEY__{connection_name}-{match_type}-{match_setting}-{key}__AGENIXKEY"
    return f"{base_folder}/{connection_name}-{match_type}-{match_setting}-{key}"


paths = ["./"]
if args.cd:
    paths = PATHS

files = list(
    chain.from_iterable(
        [
            (
                [
                    join(path, f)
                    for f in filter(
                        lambda f: f.removesuffix(NMSUFFIX) not in args.e, listdir(path)
                    )
                    if isfile(join(path, f))
                ]
            )
            for path in paths
        ]
    )
)
nmfiles = [f for f in files if f.endswith(NMSUFFIX)]

jsonConfigs = {}
secrets = []

for i in nmfiles:
    config = configparser.ConfigParser(delimiters=("=",), interpolation=None)
    config.read(i)
    connection_name = i.removesuffix(NMSUFFIX).split("/")[-1]
    jsonConfigs[connection_name] = {}
    for section in config.sections():
        jsonConfigs[connection_name][section] = {}
        for key in config[section]:
            jsonConfigs[connection_name][section][key] = config[section][key]
    if args.pwfolder is not None:
        conn = jsonConfigs[connection_name]
        for extraction in PWEXTRACTIONS:
            match_type = extraction["matchType"][0]
            match_type_1 = extraction["matchType"][1]
            if conn["connection"]["type"] == match_type:
                match_setting = extraction["matchSetting"][0]
                match_setting_1 = extraction["matchSetting"][1]
                key = extraction["key"]
                setting = conn.get(match_setting)
                if setting is not None and setting.get(key) is not None:
                    # print(f"found secret: {connection_name}:{extraction}")
                    secret_value = setting.get(key)
                    del jsonConfigs[connection_name][match_setting][key]
                    target_path = target_file_path(
                        args.pwfolder,
                        connection_name,
                        match_type_1,
                        match_setting_1,
                        key,
                    )
                    with open(target_path, "w") as file:
                        file.write(secret_value)
                    secret_dict = copy.deepcopy(extraction)
                    secret_dict["file"] = subsitute_file_path_expr(
                        args.pwfolder,
                        connection_name,
                        match_type_1,
                        match_setting_1,
                        key,
                        target_path,
                    )
                    secret_dict["matchId"] = connection_name
                    secrets.append(secret_dict)

if not args.s:
    output = to_nix(jsonConfigs)
    if args.f:
        output = format(output)
    print(output)
else:
    for key, value in jsonConfigs.items():
        with open(key + ".nix", "w") as f:
            output = to_nix(value)
            if args.f:
                output = format(output)
            f.write(output)

if not args.s:
    print(DELIMITER)
    output = to_nix(secrets)
    if args.f:
        output = format(output)
    print(output)
else:
    for secret in secrets:
        connection_name = secret["matchId"]
        match_type = secret["matchType"][1]
        setting = secret["matchSetting"][1]
        key = secret["key"]
        path = target_nix_secret_file_path(
            args.pwfolder, connection_name, match_type, match_setting, key
        )
        content = to_nix(
            {
                "matchId": connection_name,
                "matchType": match_type,
                "matchSetting": setting,
                "key": key,
                "file": secret["file"],
            }
        )
        if args.use_agenix:
            match = re.search(
                "AGENIXKEY__(?P<inner>.*)__AGENIXKEY", content, flags=re.MULTILINE
            )
            if match is not None:
                whole = match.group(0)
                inner = match.group("inner")
                content = content.replace(
                    f'"{whole}"', f'config.age.secrets."{inner}".path'
                )
                content = "config:" + content
        with open(path, "w") as f:
            f.write(content)

missing_keys = []
if args.use_agenix:
    for secret in secrets:
        connection_name = secret["matchId"]
        match_type = secret["matchType"][1]
        setting = secret["matchSetting"][1]
        key = secret["key"]
        path = target_file_path(
            args.pwfolder, connection_name, match_type, setting, key
        )
        env = os.environ.copy()
        if args.secrets_nix_path is not None:
            env["RULES"] = args.secrets_nix_path
        with open(path) as p:
            content = p.read()
            output = ""

            def run_command():
                output = check_output(
                    [
                        "agenix",
                        "-e",
                        f"{path}.age",
                    ]
                    + args.agenix_extra_args,
                    stderr=subprocess.STDOUT,
                    text=True,
                    input=content,
                    env=env,
                )
                return output

            if args.interactive_retry_agenix or args.agenix_continue_on_err:
                try:
                    output = run_command()
                except CalledProcessError as e:
                    output = e.output
                    print(e, output, file=sys.stderr)
                    if not args.agenix_continue_on_err:
                        input()
                        output = run_command()
            else:
                output = run_command()
            if args.output_missing_keys:
                match = re.search(
                    "error: attribute '(?P<inner>.*)' missing",
                    output,
                    flags=re.MULTILINE,
                )
                if match is not None:
                    missing_keys.append(match.group("inner"))


if args.output_missing_keys:
    print(DELIMITER)
    for key in missing_keys:
        print(key)
