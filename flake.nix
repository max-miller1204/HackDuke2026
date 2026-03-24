{
  description = "Circadia - On-device sleep staging via SleepFM distillation";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { nixpkgs, ... }:
  let
    systems = [ "aarch64-darwin" "x86_64-linux" "aarch64-linux" ];
    forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f {
      pkgs = nixpkgs.legacyPackages.${system};
    });
  in {
    devShells = forAllSystems ({ pkgs }: {
      default = pkgs.mkShell {
        packages = with pkgs; [
          uv
        ];

        env = {
          # Redirect all tool configs/caches into .local/ within the project
          JUPYTER_CONFIG_DIR = ".local/jupyter";
          JUPYTER_DATA_DIR = ".local/jupyter/data";
          MPLCONFIGDIR = ".local/matplotlib";
          MODAL_CONFIG_PATH = ".local/modal.toml";
          HF_HOME = ".local/huggingface";
          IPYTHONDIR = ".local/ipython";
          XDG_CACHE_HOME = ".local/cache";
        };

        shellHook = ''
          mkdir -p .local/{jupyter/data,matplotlib,cache,huggingface,ipython}

          if [ ! -d .venv ]; then
            uv venv --python python3.10
          fi
          source .venv/bin/activate
          uv sync
        '';
      };
    });
  };
}
