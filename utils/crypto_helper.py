import os
import uuid
import hashlib
import base64
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

logger = logging.getLogger("app")

class CryptoHelper:
    _key = None

    @classmethod
    def _get_derived_key(cls) -> bytes:
        """Derive a stable 256-bit machine-specific key using PBKDF2."""
        if cls._key is None:
            try:
                # Retrieve unique hardware properties
                node = str(uuid.getnode())
                system_user = os.environ.get("USERNAME", os.environ.get("USER", "default_user"))
                system_name = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "default_machine"))
                
                # Combine signature parts
                signature = f"{node}-{system_user}-{system_name}".encode('utf-8')
                
                # Derive 32-byte key
                salt = b"ResearchPaperAssistantProSalt"
                cls._key = hashlib.pbkdf2_hmac('sha256', signature, salt, 100000, 32)
            except Exception as e:
                logger.error(f"Error deriving cryptographic key: {e}")
                # Fallback static key if hardware inspection fails (prevents crashes)
                cls._key = hashlib.sha256(b"StaticFallbackKey_ResearchPaperAssistantPro").digest()
        return cls._key

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """Encrypts a string and returns a base64 encoded string."""
        if not plaintext:
            return ""
        try:
            key = cls._get_derived_key()
            cipher = AES.new(key, AES.MODE_CBC)
            iv = cipher.iv
            padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
            ciphertext = cipher.encrypt(padded_data)
            # Combine iv + ciphertext
            combined = iv + ciphertext
            return base64.b64encode(combined).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return ""

    @classmethod
    def decrypt(cls, ciphertext_b64: str) -> str:
        """Decrypts a base64 encoded encrypted string."""
        if not ciphertext_b64:
            return ""
        try:
            key = cls._get_derived_key()
            combined = base64.b64decode(ciphertext_b64.encode('utf-8'))
            if len(combined) < AES.block_size:
                return ""
            iv = combined[:AES.block_size]
            ciphertext = combined[AES.block_size:]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_padded = cipher.decrypt(ciphertext)
            decrypted = unpad(decrypted_padded, AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ""
