# Ollama CLI chatbot

A small Python chat app that talks to Ollama running on your computer. It uses
`qwen3.6:latest` by default and prints replies as they arrive. Chat history stays
in memory for the current session; `/clear` starts a fresh conversation.

## What you need

- Python 3.10 or newer (`python3 --version`)
- [Ollama](https://ollama.com/) running locally
- The `qwen3.6:latest` model installed in Ollama

Check that the model is available:

```bash
ollama list
```

If it is missing, install it with `ollama pull qwen3.6:latest`. Make sure Ollama
is running before starting the chat. On systems where Ollama does not start
automatically, run `ollama serve` in a separate terminal.

## Run the app

Open a terminal in this project folder and run:

```bash
python3 -m chatbot_cli
```

On Windows, use `py -m chatbot_cli` if `python3` is not recognised. No Python
packages need to be installed for this command.

Type a message at the `You:` prompt and press Enter. The answer appears after
`Assistant:`. Use `/help` to see commands, `/clear` to forget this session's
earlier messages, and `/exit` to quit. Chat history is not saved
when you close the app.

### Run with uv

If you use [uv](https://docs.astral.sh/uv/getting-started/installation/), run
this from the project folder:

```bash
uv run chatbot-cli
```

uv reads `pyproject.toml`, creates the project environment, and runs the
`chatbot-cli` command. You do not need to activate a virtual environment or
run `uv init` first. To pass an option, for example, use
`uv run chatbot-cli --model qwen3.6:latest`.

### Optional: install a terminal command

If you want to run `chatbot-cli` from any folder, create a virtual environment
and install this project:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
chatbot-cli
```

On Windows Command Prompt, activate it with `.venv\Scripts\activate.bat`
instead of `source ...`.
The direct `python3 -m chatbot_cli` command above does not require this step.

## Options

```bash
python3 -m chatbot_cli --model qwen3.6:latest
python3 -m chatbot_cli --host http://127.0.0.1:11434
python3 -m chatbot_cli --help
```

`--model` lets you use another model already available in Ollama. `--host`
changes the Ollama server address. The defaults are `qwen3.6:latest` and
`http://127.0.0.1:11434`.

## Troubleshooting

- **Could not connect to Ollama:** Start Ollama, then retry. If Ollama runs at a
  different address, pass it with `--host`.
- **Model not found:** Run `ollama list` and check the exact model name. Install
  it with `ollama pull qwen3.6:latest`, or pass an installed name with `--model`.
- **No text reply:** Check Ollama's output for errors and try the prompt again.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

With uv, run `uv run python -m unittest discover -s tests -v` instead.

The tests use fake Ollama responses, so they do not need a running Ollama
instance or a downloaded model.
