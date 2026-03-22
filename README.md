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