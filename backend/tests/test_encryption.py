"""Tests for encryption module."""
from app.core.encryption import EncryptionService


class TestEncryptionService:
    def setup_method(self):
        self.service = EncryptionService()

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "my-secret-api-key-12345"
        encrypted = self.service.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = self.service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertexts(self):
        plaintext = "test-secret"
        enc1 = self.service.encrypt(plaintext)
        enc2 = self.service.encrypt(plaintext)
        # Fernet includes timestamp, so ciphertexts differ
        assert enc1 != enc2

    def test_both_decrypt_to_same_value(self):
        plaintext = "test-secret"
        enc1 = self.service.encrypt(plaintext)
        enc2 = self.service.encrypt(plaintext)
        assert self.service.decrypt(enc1) == plaintext
        assert self.service.decrypt(enc2) == plaintext

    def test_empty_string(self):
        encrypted = self.service.encrypt("")
        assert self.service.decrypt(encrypted) == ""

    def test_unicode_content(self):
        plaintext = "héllo wörld 🔐"
        encrypted = self.service.encrypt(plaintext)
        assert self.service.decrypt(encrypted) == plaintext

    def test_long_content(self):
        plaintext = "x" * 10000
        encrypted = self.service.encrypt(plaintext)
        assert self.service.decrypt(encrypted) == plaintext
