from configparser import ConfigParser
from glob import glob
from json import dump
from logging import basicConfig, getLogger
from os import environ
from os.path import basename, join
from subprocess import check_output
from tempfile import NamedTemporaryFile

basicConfig(level=environ.get("LOGLEVEL", "WARNING"))
LOGGER = getLogger(__name__)

CONNECTIONS_DIRECTORIES = [
    "/etc/NetworkManager/system-connections",
    "/run/NetworkManager/system-connections",
]
EXTENSION = "nmconnection"
GLOBS = [join(directory, f"*.{EXTENSION}") for directory in CONNECTIONS_DIRECTORIES]

configs: dict[str, dict[str, dict[str, str]]] = {}

for glob_ in GLOBS:
    LOGGER.debug(f"Looping through {glob_}")
    for file_path in glob(glob_):
        LOGGER.info(f"Handling {file_path}")
        config = ConfigParser(delimiters=("=",))
        config.read(file_path)
        # Assume that there are no duplicates in `GLOBS`
        connection_name = basename(file_path).removesuffix(f".{EXTENSION}")
        configs[connection_name] = {}
        for section in config.sections():
            configs[connection_name][section] = {}
            for key in config[section]:
                configs[connection_name][section][key] = config[section][key]

with NamedTemporaryFile(mode="w") as temp_file:
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
    )  # noqa: E501
