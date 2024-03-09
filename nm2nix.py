from os import listdir
from os.path import isfile, join
import configparser
path = "./"

files = [f for f in listdir(path) if isfile(join(path, f))]
nmfiles = [f for f in files if f.endswith(".nmconnection")]

print("{")
for i in nmfiles:
    config = configparser.ConfigParser(delimiters=('=', ))
    config.read(i)
    connection_name = i.removesuffix(".nmconnection")
    print(f"  {connection_name} = {{")
    for section in config.sections():
        print(f"    {section} = {{")
        for key in config[section]:
            print(f'      {key} = "{config[section][key]}";')
        print("    };")
    print("  };")
print("};")
