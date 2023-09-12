# NetworkManager to Nix

This is a really hacky script (really please don't look at the source code) that converts every .nmconnection file in the current folder to the nix code that is expected by `networking.networkmanager.ensure-profiles.profiles` which was introduced in [NixOS/nixpkgs/#254647](https://github.com/NixOS/nixpkgs/pull/254647)

You probably want to run this script in `/etc/NetworkManager/system-connections/` (default profile storage) or `/run/NetworkManager/system-connections` (temporary profile storage) both of the files are probably only readable by the root user so you need to execute the script with root permissions aka sudo. For more details about the locations feel free to read red hats docs [here](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/assembly_networkmanager-connection-profiles-in-keyfile-format_configuring-and-managing-networking)

If you just want to run the script do:
```bash
sudo su -c "cd /etc/NetworkManager/system-connections && nix --extra-experimental-features 'nix-command flakes' run github:Janik-Haag/nm2nix"
```
