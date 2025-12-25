from subprocess import check_output
from os.path import isfile
import configparser
import tempfile
import json
import argparse
from pathlib import Path
from typing import Optional


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

class ExtractionTuple:
    file: str
    agent: str
    def __init__(self, file: str | tuple[str, str], agent: Optional[str] = None) -> None:
        if isinstance(file,tuple):
            self.file = file[0]
            self.agent = file[1]
        elif isinstance(file,str):
            self.file = file
            if agent is None:
                agent = file
            self.agent = agent
    def __repr__(self) -> str:
        return f"{self.file} -> {self.agent}"
        
        

class PwExtraction:
    matchType: ExtractionTuple
    matchSetting: ExtractionTuple
    key: str

    def __init__(self, d: dict) -> None:
        self.matchType = ExtractionTuple(d["matchType"])
        self.matchSetting = ExtractionTuple(d["matchSetting"])
        self.key = d["key"]
    def __repr__(self) -> str:
        return f"type: {self.matchType} \nsetting: {self.matchSetting} \nkey: {self.key}"

class Secret:
    matchId: str
    matchType: str
    matchSetting: str
    key: str
    file: Path
    file_expr: str

    def __init__(self, pw_extraction: PwExtraction, connection_name, base_folder_secrets: Path) -> None:
        self.matchId = connection_name
        self.matchType = pw_extraction.matchType.agent
        self.matchSetting = pw_extraction.matchSetting.agent
        self.key = pw_extraction.key
        self.file = target_file_path_secret(base_folder_secrets, connection_name, self.matchType, self.matchSetting, self.key)
        self.file_expr = target_file_path_secret_nix_expr(base_folder_secrets, connection_name, self.matchType, self.matchSetting, self.key)


# normalizing these extractions
PWEXTRACTIONS = list(map(PwExtraction, PWEXTRACTIONS))

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
parser.add_argument(
    "-e", help="file names of connections to exclude", action="append", default=[]
)

parser.add_argument(
    "-pwfolder",
    help="if given, write passwords to a secret file inside this folder, using nm-file-secret-agent to subsitute them back",
)
parser.add_argument(
    "-pwnixfolder",
    help="if given, folder where to write nix files with the expressions for \n networking.networkmanager.ensureProfiles.secrets.entries \n defaults to pwfolder",
)

args = parser.parse_args()


# returns file path where the secret should be written to
def target_file_path_secret(base_folder: Path, connection_name, match_type, match_setting, key) -> Path:
    return base_folder / f"{connection_name}-{match_type}-{match_setting}-{key}"


def target_file_path_secret_nix(base_folder: Path, connection_name, match_type, match_setting, key) -> Path:
    return base_folder / f"{connection_name}-{match_type}-{match_setting}-{key}.nix"


def target_file_path_secret_nix_expr(
    base_folder: Path, connection_name, match_type, match_setting, key
):
    return f"{target_file_path_secret(base_folder, connection_name, match_type, match_setting, key)}"

if args.pwnixfolder is None:
    args.pwnixfolder = args.pwfolder


paths = []
if args.path is None:
    paths = PATHS
else:
    paths = args.path

files = []
for path in paths:
    files += list(filter(lambda f: isfile(f) and f.stem not in args.e, Path(path).glob("*.nmconnection")))

jsonConfigs = {}
secrets = []

for i in files:
    config = configparser.ConfigParser(delimiters=('=', ), interpolation=None)
    config.read(i)
    connection_name = i.stem
    jsonConfigs[connection_name] = {}
    for section in config.sections():
        jsonConfigs[connection_name][section] = {}
        for key in config[section]:
            jsonConfigs[connection_name][section][key] = config[section][key]
    if args.pwfolder is not None:
        conn = jsonConfigs[connection_name]
        for extraction in PWEXTRACTIONS:
            match_type = extraction.matchType
            if conn["connection"]["type"] == match_type.file:
                match_setting = extraction.matchSetting
                key = extraction.key
                setting = conn.get(match_setting.file)
                if setting is not None:
                    secret_value = setting.get(key)
                    if secret_value is not None:
                        # print(f"found secret: {connection_name}:{extraction}")
                        del jsonConfigs[connection_name][match_setting.file][key]
                        secret = Secret(extraction, connection_name, Path(args.pwfolder))
                        secrets.append(secret)
                        if secret.file.exists() and not args.overwrite:
                            print(f"skipping writing secret to {secret.file} because it already exists, use -overwrite to overwrite existing files")
                            continue
                        with secret.file.open("w") as file:
                            file.write(secret_value)

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

    for secret in secrets:
        connection_name = secret.matchId
        match_type = secret.matchType
        setting = secret.matchSetting
        key = secret.key
        path = target_file_path_secret_nix(
            Path(args.pwnixfolder), connection_name, match_type, setting, key
        )
        content = json_to_nix(
            {
                "matchId": connection_name,
                "matchType": match_type,
                "matchSetting": setting,
                "key": key,
                "file": secret.file_expr,
            }
        )
        if path.exists():
            print(f"skipping writing to {path} because it already exists, use -overwrite to overwrite existing files")
        with path.open("w") as f:
            f.write(content)
