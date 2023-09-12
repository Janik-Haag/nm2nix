{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };
  outputs = { self, nixpkgs }:
  {
    packages.x86_64-linux.default = nixpkgs.legacyPackages.x86_64-linux.writers.writePython3Bin "nm2nix" { } (builtins.readFile ./nm2nix.py);
    packages.aarch64-linux.default = nixpkgs.legacyPackages.aarch64-linux.writers.writePython3Bin "nm2nix" { } (builtins.readFile ./nm2nix.py);
  };
}
