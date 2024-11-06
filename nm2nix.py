import configparser
from glob import glob
from json import dump
from logging import getLogger, basicConfig, DEBUG
from os.path import join
from subprocess import check_output
from tempfile import NamedTemporaryFile

basicConfig(level=DEBUG)
LOGGER = getLogger(__name__)

CONNECTIONS_DIRECTORY = "/etc/NetworkManager/system-connections"
EXTENSION = "nmconnection"
GLOB = join(CONNECTIONS_DIRECTORY, f"*.{EXTENSION}")

LOGGER.debug(f"Looping through {GLOB}")

configs = {}

for file_path in glob(GLOB):
    LOGGER.info(f"Handling {file_path}")
    config = configparser.ConfigParser(delimiters=("=",))
    config.read(file_path)
    connection_name = file_path.removesuffix(f".{EXTENSION}")
    configs[connection_name] = {}
    for section in config.sections():
        configs[connection_name][section] = {}
        for key in config[section]:
            configs[connection_name][section][key] = config[section][key]

with NamedTemporaryFile("w+") as temp_file:
    dump(configs, temp_file)
    temp_file.flush()

    print(
        check_output(
            [
                "nix-instantiate",
                "--expr",
                "--eval",
                f'builtins.fromJSON (builtins.readFile "{temp_file.name}")',
            ],
            text=True,
        )
    )
