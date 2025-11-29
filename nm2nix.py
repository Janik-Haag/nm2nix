from os import listdir
from subprocess import check_output
from os.path import isfile, join
import configparser
import tempfile
import json
import argparse
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

parser = argparse.ArgumentParser(
    prog="nm2nix",
    description="Converts .nmconnection files into nix code",
)

paths_list_human = ", ".join(PATHS)
parser.add_argument(
    "-cd", help=f"wether to cd to {paths_list_human}", action="store_true"
)
parser.add_argument(
    "-s", help="wether to split output to one file each", action="store_true"
)
parser.add_argument(
    "-f", help="wether to format the files / output", action="store_true"
)

args = parser.parse_args()


paths = ["./"]
if args.cd:
    paths = PATHS

files = list(
    chain.from_iterable(
        [
            ([join(path, f) for f in listdir(path) if isfile(join(path, f))])
            for path in paths
        ]
    )
)
nmfiles = [f for f in files if f.endswith(".nmconnection")]

jsonConfigs = {}

for i in nmfiles:
    config = configparser.ConfigParser(delimiters=("=",), interpolation=None)
    config.read(i)
    connection_name = i.removesuffix(".nmconnection").split("/")[-1]
    jsonConfigs[connection_name] = {}
    for section in config.sections():
        jsonConfigs[connection_name][section] = {}
        for key in config[section]:
            jsonConfigs[connection_name][section][key] = config[section][key]

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
