# src/my_agentic_app/vault/manager.py
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

from .core import EncryptedVault, VaultError
from .config import VAULT_FILE, APP_DATA_DIR

load_dotenv()

class VaultManager:
    """
    Singleton vault manager for the application.
    Handles vault lifecycle: creation, unlocking, and credential access.
    """
    
    _instance: Optional['VaultManager'] = None
    _vault: Optional[EncryptedVault] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize vault manager (only once)."""
        if self._vault is not None:
            return  # Already initialized
    
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
            return True  # Already initialized
        
        # Get master password
        if master_password is None:
            master_password = os.environ.get('VAULT_MASTER_PASSWORD')
        
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
                # Unlock existing vault
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
    
    def add_credential(self, service: str, username: str, password: str,
                       metadata: Optional[dict] = None) -> dict:
        """Add a credential."""
        return self.get_vault().add_credential(service, username, password, metadata)
    
    def get_credential(self, service: str) -> Optional[dict]:
        """Get a credential by service."""
        return self.get_vault().get_credential(service)
    
    def list_services(self) -> list:
        """List all services with stored credentials."""
        return self.get_vault().list_services()
    
    def delete_credential(self, service: str) -> bool:
        """Delete a credential."""
        return self.get_vault().delete_credential(service)
    
    def lock(self):
        """Lock the vault (clear from memory)."""
        if self._vault:
            self._vault.lock()
    
    def is_locked(self) -> bool:
        """Check if vault is locked."""
        if self._vault is None:
            return True
        return self._vault.is_locked()

# Singleton instance
vault_manager = VaultManager()
