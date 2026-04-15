import os
import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import get_settings

class EncryptionService:
    """Fernet-based encryption for API keys and secrets."""
    
    def __init__(self):
        settings = get_settings()
        # Derive Fernet key using PBKDF2 — stable across key lengths
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            settings.secret_key.encode(),
            salt=b'gnosis-encryption-v1',
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(key_material)
        self._fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string. Returns base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        return self._fernet.decrypt(ciphertext.encode()).decode()

encryption_service = EncryptionService()
