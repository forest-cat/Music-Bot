{ pkgs, lib, config, inputs, ... }:

let
  pkgs-unstable = import inputs.nixpkgs-unstable { system = pkgs.stdenv.system; };
in {

  # https://devenv.sh/basics/
  env.GREET = "Music-Bot-Environment";


  # https://devenv.sh/packages/
  packages = [ 
    pkgs.git
    pkgs.ffmpeg_6-full
    pkgs-unstable.hatch

  ];

  # https://devenv.sh/scripts/
  scripts.hello.exec = "echo hello from $GREET";

  enterShell = ''
    hello
    git --version
    python3 --version
    pip freeze
  '';

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep "2.42.0"
  '';

  # https://devenv.sh/languages/
  # languages.nix.enable = true;
  languages.python = {
    enable = true;
    version = "3.11.9";
    venv.enable = true;
    venv.requirements = ./requirements.txt;
  };
  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
