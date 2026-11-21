import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import chess

from src.voice.providers import ModelConfig, ProviderError, discover_models, complete
from src.voice.commentator import ChessCommentator
from src.voice.move_context import extract_move_context


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.reply()

            def do_POST(self):
                cls.payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.reply()

            def reply(self):
                cls.path = self.path
                cls.auth = self.headers.get("Authorization")
                self.send_response(cls.code)
                self.end_headers()
                self.wfile.write(json.dumps(cls.response).encode())

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        type(self).code = 200
        type(self).response = {}
        type(self).payload = None

    def test_lmstudio_discovery(self):
        type(self).response = {
            "data": [{"id": "local-chat"}, {"id": "embedding-model"}, {"id": "local-chat"}]
        }
        models = discover_models(ModelConfig("lmstudio", self.url + "/v1/"))
        self.assertEqual(models, ["local-chat"])
        self.assertEqual(self.path, "/v1/models")

    def test_ollama_discovery_and_chat(self):
        type(self).response = {"models": [{"name": "my-model:latest"}]}
        config = ModelConfig("ollama", self.url, "my-model:latest")
        self.assertEqual(discover_models(config), ["my-model:latest"])
        self.assertEqual(self.path, "/api/tags")
        type(self).response = {"message": {"content": "A quiet move."}}
        self.assertEqual(complete(config, [], 100), "A quiet move.")
        self.assertEqual(self.path, "/api/chat")
        self.assertFalse(self.payload["stream"])
        self.assertFalse(self.payload["think"])
        self.assertEqual(self.payload["options"]["num_predict"], 100)

    def test_remote_auth_and_selected_model(self):
        type(self).response = {"choices": [{"message": {"content": "A useful explanation."}}]}
        result = complete(ModelConfig("remote", self.url + "/v1", "chosen", "secret"), [], 256)
        self.assertEqual(result, "A useful explanation.")
        self.assertEqual(self.auth, "Bearer secret")
        self.assertEqual(self.payload["model"], "chosen")
        self.assertEqual(self.path, "/v1/chat/completions")

    def test_empty_model_list(self):
        type(self).response = {"data": []}
        self.assertEqual(discover_models(ModelConfig("lmstudio", self.url)), [])

    def test_auth_failure_is_actionable_and_redacted(self):
        type(self).code = 401
        type(self).response = {"secret": "do not display"}
        with self.assertRaisesRegex(ProviderError, "Authentication failed") as error:
            discover_models(ModelConfig("remote", self.url, api_key="secret"))
        self.assertNotIn("secret", str(error.exception))

    def test_malformed_and_empty_responses(self):
        for response in ({}, {"choices": []}, {"choices": [{"message": {"content": ""}}]}):
            type(self).response = response
            with self.assertRaises(ProviderError):
                complete(ModelConfig("lmstudio", self.url, "local"), [], 100)

    def test_reasoning_removed(self):
        type(self).response = {
            "choices": [
                {
                    "message": {
                        "content": "<think>Internal reasoning</think>White moves the pawn to e4."
                    }
                }
            ]
        }
        result = complete(ModelConfig("lmstudio", self.url, "local"), [], 100)
        self.assertEqual(result, "White moves the pawn to e4.")

    def test_no_model_name_is_invented(self):
        with self.assertRaisesRegex(ProviderError, "Choose"):
            complete(ModelConfig("lmstudio", self.url), [], 100)

    def test_invalid_urls(self):
        for url in ("file:///etc/passwd", "http://user:pass@host", "http://host?key=secret"):
            with self.assertRaises(ProviderError):
                ModelConfig("remote", url).endpoint("/models")

    def test_provider_failure_returns_explicit_fallback(self):
        context = extract_move_context(chess.Board(), chess.Move.from_uci("e2e4"))
        with patch("src.voice.commentator.complete", side_effect=ProviderError("Timed out")):
            result = ChessCommentator(ModelConfig("remote", self.url, "local")).explain(context)
        self.assertIn("fallback", result.source)
        self.assertEqual(result.error, "Timed out")
        self.assertIn("e4", result.text)

    def test_offline_never_calls_network(self):
        context = extract_move_context(chess.Board(), chess.Move.from_uci("e2e4"))
        with patch("src.voice.commentator.complete") as request:
            result = ChessCommentator().explain(context)
        request.assert_not_called()
        self.assertEqual(result.source, "Engine notes")

    def test_timeout_falls_back(self):
        context = extract_move_context(chess.Board(), chess.Move.from_uci("e2e4"))
        with patch("src.voice.providers.urlopen", side_effect=TimeoutError):
            result = ChessCommentator(ModelConfig("lmstudio", self.url, "local")).explain(context)
        self.assertIn("timed out", result.error)
