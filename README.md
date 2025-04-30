# NetworkManager to Nix

This is a dumb script that converts every .nmconnection file in the current directory to the nix code that is expected by `networking.networkmanager.ensureProfiles.profiles` which was introduced in [NixOS/nixpkgs/#254647](https://github.com/NixOS/nixpkgs/pull/254647)
You want to pipe the output of this program through some formatter, for example `nixfmt`

This script reads files in `/etc/NetworkManager/system-connections/` (default profile storage) and `/run/NetworkManager/system-connections` (temporary profile storage). Both folders are only readable by the root user, so you need to execute the script with root permissions aka sudo. For more details about the locations feel free to read [redhat's docs](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/assembly_networkmanager-connection-profiles-in-keyfile-format_configuring-and-managing-networking)

The code gets outputted as one line of nix, so you probably want to run it through a formatter like nixfmt (which the example below does).

If you just want to run the script do:
```bash
sudo su -c "cd /etc/NetworkManager/system-connections && nix --extra-experimental-features 'nix-command flakes' run github:Janik-Haag/nm2nix | nix --extra-experimental-features 'nix-command flakes' run nixpkgs#nixfmt-rfc-style"
```
