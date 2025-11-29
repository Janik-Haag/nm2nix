from os import listdir
from os.path import basename
from subprocess import check_output
from os.path import isfile, join
import configparser
import tempfile
import json
import argparse
from itertools import chain


def json_to_nix(input) -> str:
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


PATHS = [
    "/etc/NetworkManager/system-connections",
]

parser = argparse.ArgumentParser(
    prog="nm2nix",
    description="Converts .nmconnection files into nix code",
)

parser.add_argument(
    "-path",
    help=f"The Path in which to search for .nmconnection files \n supply multiple times to search in multiple paths \n defaults to: { ", ".join(PATHS)}",
    action="append",
)

args = parser.parse_args()


paths = []
if args.path is None:
    paths = PATHS
else:
    paths = args.path

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
    config = configparser.ConfigParser(delimiters=('=', ), interpolation=None)
    config.read(i)
    connection_name = basename(i).removesuffix(".nmconnection")
    jsonConfigs[connection_name] = {}
    for section in config.sections():
        jsonConfigs[connection_name][section] = {}
        for key in config[section]:
            jsonConfigs[connection_name][section][key] = config[section][key]

print(json_to_nix(jsonConfigs))
