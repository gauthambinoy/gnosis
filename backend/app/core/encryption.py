import os
import base64
from cryptography.fernet import Fernet
from app.config import get_settings

class EncryptionService:
    """Fernet-based encryption for API keys and secrets."""
    
    def __init__(self):
        settings = get_settings()
        # Derive Fernet key from secret_key
        key = base64.urlsafe_b64encode(settings.secret_key.encode()[:32].ljust(32, b'\0'))
        self._fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string. Returns base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        return self._fernet.decrypt(ciphertext.encode()).decode()

encryption_service = EncryptionService()
