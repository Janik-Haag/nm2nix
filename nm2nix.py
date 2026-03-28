from subprocess import check_output
from os.path import isfile
import configparser
import tempfile
import json
import argparse
from pathlib import Path


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
parser.add_argument(
    "-s", help="wether to output one file per connection", action="store_true"
)
TARGET_DEFAULT = "network_connections/"
parser.add_argument(
    "-target",
    help=f"path under which to save the generated files \n default to: {TARGET_DEFAULT}", default=TARGET_DEFAULT
)
parser.add_argument(
    "-overwrite", help="wether to overwrite existing files", action="store_true"
)

args = parser.parse_args()


paths = []
if args.path is None:
    paths = PATHS
else:
    paths = args.path

files = []
for path in paths:
    files += list(filter(isfile,Path(path).glob("*.nmconnection")))

jsonConfigs = {}

for i in files:
    config = configparser.ConfigParser(delimiters=('=', ), interpolation=None)
    config.read(i)
    connection_name = i.stem
    jsonConfigs[connection_name] = {}
    for section in config.sections():
        jsonConfigs[connection_name][section] = {}
        for key in config[section]:
            jsonConfigs[connection_name][section][key] = config[section][key]

if not args.s:
    print(json_to_nix(jsonConfigs))
else:
    target_dir = Path(args.target)
    if len(jsonConfigs) != 0 and not target_dir.exists():
        target_dir.mkdir()
    for key, value in jsonConfigs.items():
        target_path = target_dir / (key + ".nix")
        if target_path.exists() and not args.overwrite:
            print(f"skipping writing to {target_path} because it already exists, use -overwrite to overwrite existing files")
            continue
        with target_path.open("w") as f:
            f.write(json_to_nix(value))
