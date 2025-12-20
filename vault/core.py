# src/my_agentic_app/vault/core.py
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import base64
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

NONCE_SIZE = 12
TAG_SIZE = 16

class VaultError(Exception):
    """Custom exception for vault operations."""
    pass

class EncryptedVault:
    """
    Secure credential vault bundled with the application.
    Stores credentials in app's data directory with AES-256-GCM encryption.
    """
    
    def __init__(self, vault_path: Path, master_password: str):
        """
        Initialize vault.
        
        Args:
            vault_path: Path to vault.enc file (usually APP_DATA_DIR / "vault.enc")
            master_password: Master password for encryption/decryption
        """
        self.vault_path = vault_path
        self.master_password = master_password
        self.master_key = None
        self.vault_data = None
        self._is_locked = True
    
    def _derive_key(self, salt: Optional[bytes] = None) -> tuple:
        """
        Derive encryption key from master password using Argon2id.
        Returns (key, salt) tuple.
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = Scrypt(
            salt=salt,
            length=32,  # 256-bit key
            n=2**14,    # CPU/memory cost (16384)
            r=8,        # Block size parameter
            p=1,        # Parallelization parameter
            backend=default_backend()
        )
        key = kdf.derive(self.master_password.encode())
        return key, salt
    
    def create(self) -> bool:
        """Create a new encrypted vault file."""
        try:
            self.master_key, salt = self._derive_key()
            
            vault_content = {
                "version": 1,
                "entries": [],
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat()
                }
            }
            
            plaintext = json.dumps(vault_content).encode()
            nonce = secrets.token_bytes(NONCE_SIZE)
            
            cipher = AESGCM(self.master_key)
            ciphertext = cipher.encrypt(nonce, plaintext, None)
            
            vault_bytes = salt + nonce + ciphertext
            
            with open(self.vault_path, 'wb') as f:
                f.write(vault_bytes)
            
            os.chmod(self.vault_path, 0o600)
            self.vault_data = vault_content
            self._is_locked = False
            
            return True
        except Exception as e:
            raise VaultError(f"Failed to create vault: {e}")
    
    def unlock(self) -> bool:
        """Decrypt and load vault into memory."""
        try:
            if not self.vault_path.exists():
                raise VaultError(f"Vault file not found: {self.vault_path}")
            
            with open(self.vault_path, 'rb') as f:
                vault_bytes = f.read()
            
            if len(vault_bytes) < 28:
                raise VaultError("Invalid vault file (corrupted or too small)")
            
            salt = vault_bytes[:16]
            nonce = vault_bytes[16:28]
            ciphertext = vault_bytes[28:]
            
            self.master_key, _ = self._derive_key(salt)
            
            cipher = AESGCM(self.master_key)
            plaintext = cipher.decrypt(nonce, ciphertext, None)
            
            self.vault_data = json.loads(plaintext.decode())
            self._is_locked = False
            return True
        
        except Exception as e:
            raise VaultError(f"Failed to unlock vault (wrong password?): {e}")
    
    def lock(self):
        """Clear vault data from memory."""
        self.vault_data = None
        self.master_key = None
        self._is_locked = True
    
    def save(self) -> bool:
        """Re-encrypt and persist vault to disk."""
        try:
            if self._is_locked or self.vault_data is None:
                raise VaultError("Vault is locked; cannot save")
            
            plaintext = json.dumps(self.vault_data).encode()
            nonce = secrets.token_bytes(NONCE_SIZE)
            
            cipher = AESGCM(self.master_key)
            ciphertext = cipher.encrypt(nonce, plaintext, None)
            
            # Reuse salt from existing vault
            with open(self.vault_path, 'rb') as f:
                existing = f.read()
            salt = existing[:16]
            
            vault_bytes = salt + nonce + ciphertext
            
            with open(self.vault_path, 'wb') as f:
                f.write(vault_bytes)
            
            os.chmod(self.vault_path, 0o600)
            self.vault_data["metadata"]["last_modified"] = datetime.now().isoformat()
            return True
        
        except Exception as e:
            raise VaultError(f"Failed to save vault: {e}")
    
    def add_credential(self, service: str, username: str, password: str,
                       metadata: Optional[Dict] = None) -> Dict:
        """
        Add a credential entry.
        
        Args:
            service: Service/app name (e.g., 'openai_api', 'github_token')
            username: Username or key identifier
            password: Password or secret token
            metadata: Optional additional metadata
        """
        if self._is_locked:
            raise VaultError("Vault is locked")
        
        entry = {
            "id": len(self.vault_data["entries"]) + 1,
            "service": service,
            "username": username,
            "password": password,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.vault_data["entries"].append(entry)
        self.save()
        return entry
    
    def get_credential(self, service: str) -> Optional[Dict]:
        """Retrieve a credential by service name."""
        if self._is_locked:
            raise VaultError("Vault is locked")
        
        for entry in self.vault_data["entries"]:
            if entry["service"].lower() == service.lower():
                return entry
        return None
    
    def list_services(self) -> List[str]:
        """List all stored services."""
        if self._is_locked:
            return []
        return [e["service"] for e in self.vault_data["entries"]]
    
    def delete_credential(self, service: str) -> bool:
        """Delete a credential by service name."""
        if self._is_locked:
            raise VaultError("Vault is locked")
        
        original_count = len(self.vault_data["entries"])
        self.vault_data["entries"] = [
            e for e in self.vault_data["entries"]
            if e["service"].lower() != service.lower()
        ]
        
        if len(self.vault_data["entries"]) < original_count:
            self.save()
            return True
        return False
    
    def is_locked(self) -> bool:
        """Check if vault is locked."""
        return self._is_locked
