from typing import Optional, Dict, List
import os
from dotenv import load_dotenv

from .core import EncryptedVault, VaultError
from .config import VAULT_FILE, APP_DATA_DIR

load_dotenv()


class VaultManager:
    """
    Singleton vault manager for the application.
    Handles vault lifecycle with unstructured JSON storage.
    """

    _instance: Optional["VaultManager"] = None
    _vault: Optional[EncryptedVault] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._vault is not None:
            return

    def initialize(self, master_password: Optional[str] = None) -> bool:
        """
        Initialize vault: create if doesn't exist, unlock if does.
        
        Args:
            master_password: Master password. If None, get from VAULT_MASTER_PASSWORD env var
        
        Returns:
            True if initialization successful
        """
        if self._vault is not None:
            return True

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

    def add_credential(self, entry_data: Dict) -> Dict:
        """
        Add unstructured credential entry.
        
        Args:
            entry_data: Dict with arbitrary fields. Must include non-empty 'service' field.
                       Optional 'ttl_seconds' for expiration.
        
        Example:
            vm.add_credential({
                "service": "github",
                "username": "user",
                "token": "ghp_xyz",
                "scopes": ["repo", "user"],
                "ttl_seconds": 3600
            })
        """
        return self.get_vault().add_credential(entry_data)

    def update_credential(self, service: str, updates: Dict) -> Optional[Dict]:
        """
        Update existing credential by merging new fields.
        
        Args:
            service: Service name
            updates: Dict of fields to merge. Can include 'ttl_seconds'.
        
        Returns:
            Updated entry or None if not found/expired
        
        Example:
            vm.update_credential("github", {
                "token": "ghp_new",
                "updated_note": "rotated token",
                "ttl_seconds": 7200
            })
        """
        return self.get_vault().update_credential(service, updates)

    def get_credential(self, service: str, *, purge_if_expired: bool = True) -> Optional[Dict]:
        """Get credential entry by service name."""
        return self.get_vault().get_credential(service, purge_if_expired=purge_if_expired)

    def get_service_fields(self, service: str) -> Optional[List[str]]:
        """
        Get list of field names for a service (without values).
        
        Returns:
            List of field names, or None if service not found/expired
        
        Example:
            fields = vm.get_service_fields("github")
            # ['service', 'username', 'token', 'scopes', 'created_at', 'updated_at']
        """
        return self.get_vault().get_service_fields(service)

    def list_services(self, *, include_expired: bool = False) -> List[str]:
        """List all service names."""
        return self.get_vault().list_services(include_expired=include_expired)

    def delete_credential(self, service: str) -> bool:
        """Delete a credential by service name."""
        return self.get_vault().delete_credential(service)

    def purge_expired(self) -> int:
        """Purge all expired entries; returns count removed."""
        return self.get_vault().purge_expired()

    def lock(self):
        """Lock the vault (clear from memory)."""
        if self._vault:
            self._vault.lock()

    def is_locked(self) -> bool:
        """Check if vault is locked."""
        if self._vault is None:
            return True
        return self._vault.is_locked()


vault_manager = VaultManager()
