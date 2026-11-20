"""Tests use a fake Gemini transport; no provider requests or shared DB writes."""
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chatbot_server as app

class RouterTest(unittest.TestCase):
    def test_valid_input(self):
        self.assertEqual(app.validate_input({"question":"어머니 돌봄 신청", "current_pid":""}), ("어머니 돌봄 신청", ""))
    def test_private_rejected(self):
        for q in ("123456-1234567", "010-1234-5678", "abc@example.com", "계좌번호", "비밀번호"):
            with self.subTest(q=q), self.assertRaises(ValueError):
                app.validate_input({"question":q})
    def test_no_case_payload(self):
        with self.assertRaises(ValueError):
            app.validate_input({"question":"신청", "cases":[]})
    def test_length_and_id(self):
        for bad in ({"question":""}, {"question":"가"*501}, {"question":"신청","current_pid":"fake"}):
            with self.assertRaises(ValueError):
                app.validate_input(bad)
    def test_model_not_configured(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY":"", "GEMINI_MODEL":""}):
            with self.assertRaises(app.ConfigError):
                app.model_config()
    def test_default_model(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY":"synthetic-test-key", "GEMINI_MODEL":""}):
            self.assertEqual(app.model_config(), ("synthetic-test-key", app.DEFAULT_MODEL))
    def test_model_route_whitelist(self):
        for r in ({"intent":"send","pid":"s1"}, {"intent":"docs","pid":"other"}, {"intent":"docs","pid":"s1","answer":"fake"}):
            with self.assertRaises(ValueError):
                app.validate_route(r)
    def test_model_transport_and_result(self):
        def fake(req, timeout):
            self.assertEqual(timeout,18)
            self.assertTrue(req.full_url.endswith("/gemini-test:generateContent"))
            self.assertEqual(req.get_header("X-goog-api-key"), "synthetic-test-key")
            data=json.loads(req.data)
            q=json.loads(data["contents"][0]["parts"][0]["text"])
            self.assertEqual(set(q), {"services","current_pid","question"})
            self.assertEqual(q["question"], "어머니 돌봄 신청")
            self.assertNotIn("synthetic-test-key", req.full_url)
            return io.BytesIO(json.dumps({"candidates":[{"content":{"parts":[{"text":'{"intent":"apply","pid":"s2"}'}]}}]}).encode())
        with patch.dict(os.environ, {"GEMINI_API_KEY":"synthetic-test-key","GEMINI_MODEL":"gemini-test"}):
            self.assertEqual(app.classify("어머니 돌봄 신청","",fake), {"intent":"apply","pid":"s2"})
    def test_invalid_provider_response(self):
        def fake(req, timeout):
            return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"not JSON"}]}}]}')
        with patch.dict(os.environ, {"GEMINI_API_KEY":"synthetic-test-key","GEMINI_MODEL":"gemini-test"}):
            with self.assertRaises(ValueError):
                app.classify("서류","s1",fake)

if __name__ == "__main__":
    unittest.main()
