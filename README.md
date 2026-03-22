# Circadia

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Clone the repo and set up the environment:
   ```sh
   git clone --recurse-submodules <repo-url>
   cd circadia
   uv venv
   uv sync
   source .venv/bin/activate
   ```

## Data

1. Download the Sleep-EDF Expanded dataset (SC subjects) from [PhysioNet](https://physionet.org/content/sleep-edfx/1.0.0/) and place the `.edf` files in `data/`:
   ```sh
   data/
   ├── SC4001E0-PSG.edf
   ├── SC4001EC-Hypnogram.edf
   ├── SC4002E0-PSG.edf
   ├── SC4002EC-Hypnogram.edf
   └── ...
   ```

2. Run preprocessing to generate embeddings and labels in `data/processed/`:
   ```sh
   uv run python -m src.preprocess
   ```

## Running

Train the model on Modal (requires a [Modal](https://modal.com/) account and `modal token set`):

```sh
uv run modal run src/modal_app.py
```

### Auto-activation (optional)

Install [direnv](https://direnv.net/) so the venv activates automatically when you `cd` into the project:

```sh
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc
direnv allow
```