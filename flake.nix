{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
  in
  {
    packages.x86_64-linux.default = pkgs.writers.writePython3Bin "nm2nix" { } (builtins.readFile ./nm2nix.py);
    packages.aarch64-linux.default = pkgs.writers.writePython3Bin "nm2nix" { } (builtins.readFile ./nm2nix.py);
  };
}
