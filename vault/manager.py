from typing import Optional
import os
from dotenv import load_dotenv

from .core import EncryptedVault, VaultError
from .config import VAULT_FILE, APP_DATA_DIR  # keep if you use APP_DATA_DIR elsewhere

load_dotenv()


class VaultManager:
    """
    Singleton vault manager for the application.
    Handles vault lifecycle: creation, unlocking, and credential access.
    """

    _instance: Optional["VaultManager"] = None
    _vault: Optional[EncryptedVault] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize vault manager (only once)."""
        if self._vault is not None:
            return

    def initialize(self, master_password: Optional[str] = None) -> bool:
        """
        Initialize vault: create if doesn't exist, unlock if does.
        
        Args:
            master_password: Master password. If None, try to get from:
                1. VAULT_MASTER_PASSWORD env var
                2. .env file
                3. Prompt user (if interactive)
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._vault is not None:
            return True

        # Get master password
        if master_password is None:
            master_password = os.environ.get("VAULT_MASTER_PASSWORD")

        if not master_password:
            raise VaultError(
                "No master password provided. Set VAULT_MASTER_PASSWORD env var or pass to initialize()"
            )

        try:
            self._vault = EncryptedVault(VAULT_FILE, master_password)
            # Create new vault if doesn't exist
            if not VAULT_FILE.exists():
                print(f"Creating new vault at {VAULT_FILE}")
                self._vault.create()
            else:
                #Unlock existing vault
                self._vault.unlock()
            return True
        except VaultError as e:
            print(f"Vault initialization failed: {e}")
            return False

    def get_vault(self) -> EncryptedVault:
        """Get the vault instance (must be initialized first)."""
        if self._vault is None:
            raise VaultError("Vault not initialized. Call initialize() first.")
        return self._vault

    def add_credential(
        self,
        service: str,
        username: str,
        password: str,
        metadata: Optional[dict] = None,
        ttl_seconds: Optional[int] = None,
    ) -> dict:
        return self.get_vault().add_credential(service, username, password, metadata, ttl_seconds)

    def get_credential(self, service: str, *, purge_if_expired: bool = True) -> Optional[dict]:
        return self.get_vault().get_credential(service, purge_if_expired=purge_if_expired)

    def list_services(self, *, include_expired: bool = False) -> list:
        return self.get_vault().list_services(include_expired=include_expired)

    def delete_credential(self, service: str) -> bool:
        return self.get_vault().delete_credential(service)

    def purge_expired(self) -> int:
        return self.get_vault().purge_expired()

    def lock(self):
        if self._vault:
            self._vault.lock()

    def is_locked(self) -> bool:
        if self._vault is None:
            return True
        return self._vault.is_locked()


vault_manager = VaultManager()
