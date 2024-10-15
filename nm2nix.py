from os import listdir
from subprocess import check_output
from os.path import isfile, join
import configparser
import tempfile
import json

path = "./"

files = [f for f in listdir(path) if isfile(join(path, f))]
nmfiles = [f for f in files if f.endswith(".nmconnection")]

jsonConfigs = {}

for i in nmfiles:
    config = configparser.ConfigParser(delimiters=('=', ))
    config.read(i)
    connection_name = i.removesuffix(".nmconnection")
    jsonConfigs[connection_name] = {}
    for section in config.sections():
        jsonConfigs[connection_name][section] = {}
        for key in config[section]:
            jsonConfigs[connection_name][section][key] = config[section][key]

with tempfile.NamedTemporaryFile(mode="w") as tf:
    tf.write(json.dumps(jsonConfigs))
    tf.flush()
    print(check_output(["nix-instantiate", "--expr", "--eval",  f"builtins.fromJSON (builtins.readFile \"{tf.name}\")"], text=True))  # noqa: E501
