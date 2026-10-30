"""Tests for the Ollama protocol and interactive session."""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from chatbot_cli.app import DEFAULT_MODEL, OllamaError, main, stream_chat


class FakeResponse:
    def __init__(self, *events: dict[str, object]) -> None:
        self.lines = [json.dumps(event).encode("utf-8") + b"\n" for event in events]

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __iter__(self):
        return iter(self.lines)


class StreamChatTests(unittest.TestCase):
    def test_sends_model_and_history_and_streams_reply(self) -> None:
        messages = [{"role": "user", "content": "Hello"}]
        chunks: list[str] = []
        response = FakeResponse(
            {"message": {"content": "Hi"}, "done": False},
            {"message": {"content": " there"}, "done": False},
            {"message": {"content": ""}, "done": True},
        )
        with patch("chatbot_cli.app.request.urlopen", return_value=response) as urlopen:
            reply = stream_chat(messages, DEFAULT_MODEL, "http://localhost:11434", chunks.append)

        sent_request = urlopen.call_args.args[0]
        self.assertEqual(sent_request.full_url, "http://localhost:11434/api/chat")
        self.assertEqual(
            json.loads(sent_request.data),
            {"model": DEFAULT_MODEL, "messages": messages, "stream": True},
        )
        self.assertEqual(chunks, ["Hi", " there"])
        self.assertEqual(reply, "Hi there")

    def test_reports_missing_model_from_http_error(self) -> None:
        error = HTTPError(
            "http://localhost:11434/api/chat",
            404,
            "Not Found",
            {},
            io.BytesIO(b'{"error":"model not found"}'),
        )
        with patch("chatbot_cli.app.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(OllamaError, "HTTP 404: model not found"):
                stream_chat([], DEFAULT_MODEL, "http://localhost:11434", lambda _: None)

    def test_reports_connection_failure(self) -> None:
        with patch("chatbot_cli.app.request.urlopen", side_effect=URLError("refused")):
            with self.assertRaisesRegex(OllamaError, "Could not connect to Ollama"):
                stream_chat([], DEFAULT_MODEL, "http://localhost:11434", lambda _: None)

    def test_rejects_incomplete_stream(self) -> None:
        response = FakeResponse({"message": {"content": "partial"}, "done": False})
        with patch("chatbot_cli.app.request.urlopen", return_value=response):
            with self.assertRaisesRegex(OllamaError, "before finishing"):
                stream_chat([], DEFAULT_MODEL, "http://localhost:11434", lambda _: None)


class InteractiveTests(unittest.TestCase):
    def test_preserves_history_until_clear(self) -> None:
        captured: list[list[dict[str, str]]] = []

        def fake_chat(messages, _model, _host, on_chunk):
            captured.append(messages)
            on_chunk("reply")
            return "reply"

        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=["first", "second", "/clear", "third", "/exit"]),
            patch("chatbot_cli.app.stream_chat", side_effect=fake_chat),
            redirect_stdout(output),
        ):
            result = main([])

        self.assertEqual(result, 0)
        self.assertEqual(captured[0], [{"role": "user", "content": "first"}])
        self.assertEqual(
            captured[1],
            [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "reply"},
                {"role": "user", "content": "second"},
            ],
        )
        self.assertEqual(captured[2], [{"role": "user", "content": "third"}])
        self.assertIn("Conversation cleared.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
