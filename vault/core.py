import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import secrets

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

NONCE_SIZE = 12
TAG_SIZE = 16


class VaultError(Exception):
    """Custom exception for vault operations."""
    pass


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _dt_to_iso(dt: datetime) -> str:
    # Always store timezone-aware UTC times
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _iso_to_dt(s: str) -> datetime:
    # Accept ISO strings with or without timezone; treat naive as UTC
    # Also accept a trailing 'Z' if you ever write that later.
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
            length=32,      # 256-bit key
            n=2**14,        # CPU/memory cost
            r=8,            # Block size parameter
            p=1,            # Parallelization parameter
            backend=default_backend()
        )
        key = kdf.derive(self.master_password.encode())
        return key, salt

    def create(self) -> bool:
        try:
            self.master_key, salt = self._derive_key()

            vault_content = {
                "version": 2,  # bump version (older vaults still load)
                "entries": [],
                "metadata": {
                    "created": _dt_to_iso(_now_utc()),
                    "last_modified": _dt_to_iso(_now_utc())
                }
            }

            plaintext = json.dumps(vault_content).encode()
            nonce = secrets.token_bytes(NONCE_SIZE)

            cipher = AESGCM(self.master_key)
            ciphertext = cipher.encrypt(nonce, plaintext, None)

            vault_bytes = salt + nonce + ciphertext

            with open(self.vault_path, "wb") as f:
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

            with open(self.vault_path, "rb") as f:
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

            # Backward compatibility: ensure expected keys exist
            self.vault_data.setdefault("version", 1)
            self.vault_data.setdefault("entries", [])
            self.vault_data.setdefault("metadata", {})
            self.vault_data["metadata"].setdefault("created", _dt_to_iso(_now_utc()))
            self.vault_data["metadata"].setdefault("last_modified", _dt_to_iso(_now_utc()))

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

            # Update last_modified BEFORE encrypting
            self.vault_data.setdefault("metadata", {})
            self.vault_data["metadata"]["last_modified"] = _dt_to_iso(_now_utc())

            plaintext = json.dumps(self.vault_data).encode()
            nonce = secrets.token_bytes(NONCE_SIZE)

            cipher = AESGCM(self.master_key)
            ciphertext = cipher.encrypt(nonce, plaintext, None)

            # Reuse salt from existing vault
            with open(self.vault_path, "rb") as f:
                existing = f.read()
            salt = existing[:16]

            vault_bytes = salt + nonce + ciphertext

            with open(self.vault_path, "wb") as f:
                f.write(vault_bytes)

            os.chmod(self.vault_path, 0o600)
            return True
        except Exception as e:
            raise VaultError(f"Failed to save vault: {e}")

    def _is_entry_expired(self, entry: Dict, now: Optional[datetime] = None) -> bool:
        now = now or _now_utc()
        expires_at = entry.get("expires_at", None)
        if not expires_at:
            return False  # infinite TTL
        try:
            exp_dt = _iso_to_dt(expires_at)
        except Exception:
            # If malformed expires_at exists, treat as error (safer) or expired.
            raise VaultError(f"Malformed expires_at for service '{entry.get('service')}': {expires_at}")
        return now >= exp_dt

    def purge_expired(self) -> int:
        """Delete expired entries from the vault; returns count removed."""
        if self._is_locked:
            raise VaultError("Vault is locked")

        now = _now_utc()
        before = len(self.vault_data["entries"])
        self.vault_data["entries"] = [e for e in self.vault_data["entries"] if not self._is_entry_expired(e, now)]
        removed = before - len(self.vault_data["entries"])
        if removed > 0:
            self.save()
        return removed

    def add_credential(
        self,
        service: str,
        username: str,
        password: str,
        metadata: Optional[Dict] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Dict:
        """
        Add a credential entry.
        
        Args:
            service: Service/app name (e.g., 'openai_api', 'github_token')
            username: Username or key identifier
            password: Password or secret token
            metadata: Optional additional metadata

        ttl_seconds:
          - None => infinite
          - int > 0 => expires now + ttl_seconds
          - 0 or negative => treated as already-expired (will be purged on read)
        """
        if self._is_locked:
            raise VaultError("Vault is locked")

        now = _now_utc()
        expires_at: Optional[str] = None
        if ttl_seconds is not None:
            expires_at = _dt_to_iso(now + timedelta(seconds=int(ttl_seconds)))

        entry = {
            "id": len(self.vault_data["entries"]) + 1,
            "service": service,
            "username": username,
            "password": password,
            "metadata": metadata or {},
            "expires_at": expires_at,           # NEW FIELD
            "created_at": _dt_to_iso(now),
            "updated_at": _dt_to_iso(now),
        }

        self.vault_data["entries"].append(entry)
        self.save()
        return entry

    def get_credential(self, service: str, *, purge_if_expired: bool = True) -> Optional[Dict]:
        """Retrieve a credential by service name."""
        if self._is_locked:
            raise VaultError("Vault is locked")

        now = _now_utc()
        for i, entry in enumerate(self.vault_data["entries"]):
            if entry.get("service", "").lower() != service.lower():
                continue

            if self._is_entry_expired(entry, now):
                if purge_if_expired:
                    # delete expired entry and persist
                    self.vault_data["entries"].pop(i)
                    self.save()
                return None

            return entry

        return None

    def list_services(self, *, include_expired: bool = False) -> List[str]:
        if self._is_locked:
            return []

        now = _now_utc()
        services: List[str] = []
        for e in self.vault_data["entries"]:
            if include_expired or not self._is_entry_expired(e, now):
                services.append(e.get("service"))
        return services

    def delete_credential(self, service: str) -> bool:
        """Delete a credential by service name; returns True if deleted."""
        if self._is_locked:
            raise VaultError("Vault is locked")

        original_count = len(self.vault_data["entries"])
        self.vault_data["entries"] = [
            e for e in self.vault_data["entries"]
            if e.get("service", "").lower() != service.lower()
        ]

        if len(self.vault_data["entries"]) < original_count:
            self.save()
            return True
        return False

    def is_locked(self) -> bool:
        """Check if vault is locked."""
        return self._is_locked
