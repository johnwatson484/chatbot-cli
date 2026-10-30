"""Interactive command-line chat using Ollama's local HTTP API."""

import argparse
import json
from collections.abc import Callable, Sequence
from urllib import error, request

DEFAULT_MODEL = "qwen3.6:latest"
DEFAULT_HOST = "http://127.0.0.1:11434"


class OllamaError(Exception):
    """An Ollama request failed or returned an unusable response."""


def stream_chat(
    messages: list[dict[str, str]],
    model: str,
    host: str,
    on_chunk: Callable[[str], None],
) -> str:
    """Stream one assistant reply and return its complete text."""
    body = json.dumps(
        {"model": model, "messages": messages, "stream": True}
    ).encode("utf-8")
    chat_request = request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    parts: list[str] = []
    finished = False

    try:
        with request.urlopen(chat_request, timeout=120) as response:
            for line in response:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise OllamaError("Ollama sent an invalid response.") from exc

                if not isinstance(event, dict):
                    raise OllamaError("Ollama sent an invalid response.")
                if event.get("error"):
                    raise OllamaError(str(event["error"]))

                message = event.get("message", {})
                if not isinstance(message, dict):
                    raise OllamaError("Ollama sent an invalid response.")
                chunk = message.get("content", "")
                if not isinstance(chunk, str):
                    raise OllamaError("Ollama sent an invalid response.")
                if chunk:
                    parts.append(chunk)
                    on_chunk(chunk)
                if event.get("done") is True:
                    finished = True
                    break
    except error.HTTPError as exc:
        detail = exc.reason
        try:
            payload = json.load(exc)
            if isinstance(payload, dict):
                detail = payload.get("error", detail)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise OllamaError(
            f"Could not connect to Ollama at {host}: {exc.reason}. "
            "Start Ollama and check the --host address."
        ) from exc
    except TimeoutError as exc:
        raise OllamaError("Ollama timed out while generating a reply.") from exc

    if not finished:
        raise OllamaError("Ollama closed the connection before finishing its reply.")
    if not parts:
        raise OllamaError("Ollama finished without a text reply.")
    return "".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    """Run an interactive chat session."""
    parser = argparse.ArgumentParser(
        prog="chatbot-cli", description="Chat with a local Ollama model."
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"model name (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help=f"Ollama address (default: {DEFAULT_HOST})"
    )
    args = parser.parse_args(argv)

    history: list[dict[str, str]] = []
    print(f"Chatting with {args.model}. Type /help for commands.")
    while True:
        try:
            prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return 0

        command = prompt.lower()
        if command in {"/exit", "/quit"}:
            print("Goodbye!")
            return 0
        if command == "/help":
            print("/clear  Start a new conversation\n/exit   Quit (also /quit or Ctrl+D)")
            continue
        if command == "/clear":
            history.clear()
            print("Conversation cleared.")
            continue
        if not prompt:
            continue

        next_messages = [*history, {"role": "user", "content": prompt}]
        print("Assistant: ", end="", flush=True)
        try:
            reply = stream_chat(
                next_messages,
                args.model,
                args.host,
                lambda chunk: print(chunk, end="", flush=True),
            )
        except OllamaError as exc:
            print(f"\nError: {exc}")
            continue
        except KeyboardInterrupt:
            print("\nReply interrupted.")
            continue

        print("\n")
        history = [*next_messages, {"role": "assistant", "content": reply}]
