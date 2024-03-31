from os import listdir, getpid
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

tf = tempfile.TemporaryFile("w+")
jsonConfigs = json.dump(jsonConfigs, tf)
tf.flush()


print(check_output(["nix-instantiate", "--expr", "--eval",  f"builtins.fromJSON (builtins.readFile \"/proc/{getpid()}/fd/{tf.fileno()}\")"], text=True))  # noqa: E501
