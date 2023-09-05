{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    naersk.url = "github:nix-community/naersk";
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, flake-utils, naersk, nixpkgs }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = (import nixpkgs) {
          inherit system;
        };

        naersk' = pkgs.callPackage naersk {};

      in rec {
        # For `nix build` & `nix run`:
        defaultPackage = naersk'.buildPackage {
          src = ./.;
          doCheck = false;
          buildInputs = [ pkgs.systemd ];
          nativeBuildInputs = [ pkgs.pkg-config ];
        };

        # For `nix develop` (optional, can be skipped):
        devShell = pkgs.mkShell {
          buildInputs = [ pkgs.systemd ];
          nativeBuildInputs = with pkgs; [ rustc cargo pkg-config ];
        };
      }
    );
}
