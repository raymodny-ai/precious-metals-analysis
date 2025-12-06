"""
Data Encryption Utilities
敏感数据加密 - 优化项 #8
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .settings import settings
from .logger import setup_logging

logger = setup_logging("encryption")


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive data
    
    Uses Fernet symmetric encryption (AES-128-CBC)
    """
    
    def __init__(self, key: Optional[str] = None):
        self._key = key or settings.encryption_key
        self._cipher: Optional[Fernet] = None
        
        if self._key:
            self._init_cipher()
    
    def _init_cipher(self):
        """Initialize Fernet cipher"""
        try:
            # If key is already valid Fernet key, use directly
            if len(self._key) == 44:
                self._cipher = Fernet(self._key.encode())
            else:
                # Derive key from password
                key = self._derive_key(self._key)
                self._cipher = Fernet(key)
            
            logger.info("Encryption service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
    
    def _derive_key(self, password: str, salt: bytes = None) -> bytes:
        """Derive encryption key from password"""
        salt = salt or b'precious_metals_salt'  # In production, use random salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key"""
        return Fernet.generate_key().decode()
    
    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt plaintext string
        
        Returns base64-encoded ciphertext
        """
        if not self._cipher:
            logger.warning("Encryption not configured, returning plaintext")
            return plaintext
        
        try:
            ciphertext = self._cipher.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(ciphertext).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        Decrypt ciphertext string
        
        Expects base64-encoded input
        """
        if not self._cipher:
            logger.warning("Encryption not configured, returning ciphertext")
            return ciphertext
        
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode())
            plaintext = self._cipher.decrypt(decoded)
            return plaintext.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def is_configured(self) -> bool:
        """Check if encryption is properly configured"""
        return self._cipher is not None


# Global encryption service
encryption = EncryptionService()


# ============================================================================
# Convenience Functions
# ============================================================================

def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage"""
    if not encryption.is_configured():
        # Hash if encryption not available
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()
    return encryption.encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """Decrypt a stored API key"""
    if not encryption.is_configured():
        logger.warning("Cannot decrypt: encryption not configured")
        return None
    return encryption.decrypt(encrypted_key)


def mask_sensitive(value: str, show_chars: int = 4) -> str:
    """
    Mask sensitive data for logging
    
    Example: "sk-abc123xyz" -> "sk-a***xyz"
    """
    if not value or len(value) <= show_chars * 2:
        return "***"
    
    return f"{value[:show_chars]}***{value[-show_chars:]}"


# ============================================================================
# Password Hashing (using existing passlib)
# ============================================================================

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


if __name__ == "__main__":
    print("Testing Encryption Service...")
    
    # Generate a key
    key = EncryptionService.generate_key()
    print(f"Generated key: {key[:20]}...")
    
    # Test encryption
    service = EncryptionService(key)
    
    original = "my_secret_api_key_12345"
    encrypted = service.encrypt(original)
    decrypted = service.decrypt(encrypted)
    
    print(f"Original: {original}")
    print(f"Encrypted: {encrypted[:30]}...")
    print(f"Decrypted: {decrypted}")
    print(f"Match: {original == decrypted}")
    
    # Test masking
    print(f"Masked: {mask_sensitive(original)}")
    
    # Test password hashing
    hashed = hash_password("mypassword123")
    print(f"Password hash: {hashed[:30]}...")
    print(f"Verify: {verify_password('mypassword123', hashed)}")
    
    print("\nEncryption test complete!")
