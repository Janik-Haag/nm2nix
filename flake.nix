{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };
  outputs =
    { self, nixpkgs }:
    let
      allSystems = [
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems =
        function:
        nixpkgs.lib.genAttrs allSystems (
          system:
          function {
            pkgs = import nixpkgs { inherit system; };
          }
        );
    in
    {
      packages = forAllSystems (
        { pkgs }:
        {
          default = pkgs.writers.writePython3Bin "nm2nix" { } (builtins.readFile ./nm2nix.py);
        }
      );
      devShells = forAllSystems (
        { pkgs }:
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.black
              pkgs.isort
              pkgs.nixfmt-rfc-style
              pkgs.ruff
            ];
            shellHook = ''
              ln --force --no-target-directory --symbolic "${pkgs.python3}/bin/python" python
            '';
          };
        }
      );
    };
}
