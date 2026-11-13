import unittest

from pydantic import ValidationError

from backend.config import Settings
from backend.schemas.chat import ChatRequest


class ChatRequestValidationTests(unittest.TestCase):
    def test_message_is_trimmed(self):
        request = ChatRequest(message="  Sannu  ")
        self.assertEqual(request.message, "Sannu")

    def test_blank_message_is_rejected(self):
        with self.assertRaises(ValidationError):
            ChatRequest(message="   ")

    def test_message_over_limit_is_rejected(self):
        with self.assertRaises(ValidationError):
            ChatRequest(message="a" * 2001)


class CorsConfigurationTests(unittest.TestCase):
    def test_explicit_origins_are_parsed(self):
        settings = Settings(
            _env_file=None,
            ALLOWED_ORIGINS="https://example.com,https://app.example.com",
        )
        self.assertEqual(
            settings.cors_origins,
            ["https://example.com", "https://app.example.com"],
        )

    def test_wildcard_origin_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, ALLOWED_ORIGINS="*")


if __name__ == "__main__":
    unittest.main()
