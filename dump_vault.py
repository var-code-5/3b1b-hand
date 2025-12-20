#!/usr/bin/env python3
"""
Dump all credentials from the vault and print them to CLI.

Usage:
    VAULT_MASTER_PASSWORD="your_password" python dump_vault.py
"""

import os
import sys
from pathlib import Path

# Adjust if your layout differs. Add project root to sys.path so `import vault` and
# other local packages resolve correctly whether or not a `src/` layout is used.
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from vault.manager import VaultManager, VaultError  # update package name if different
from vault.config import VAULT_FILE  # uses your existing VAULT_FILE path


def main():
    print(f"\n=== Vault Dump ===")
    print(f"Vault file: {VAULT_FILE}")

    master_pass = "TestPassword123!@#"
    if not master_pass:
        print("ERROR: VAULT_MASTER_PASSWORD env var not set.")
        sys.exit(1)

    manager = VaultManager()
    try:
        # Use your existing manager.initialize logic
        if not manager.initialize(master_password=master_pass):
            print("ERROR: Failed to initialize/unlock vault.")
            sys.exit(1)

        services = manager.list_services()
        if not services:
            print("Vault is empty.")
            return

        print(f"\nFound {len(services)} services:\n")
        for service in services:
            entry = manager.get_credential(service)
            if not entry:
                continue
            print("--------------------------------------------------")
            print(f"Service : {entry.get('service')}")
            print(f"Username: {entry.get('username')}")
            print(f"Password: {entry.get('password')}")
            metadata = entry.get("metadata")
            if metadata:
                print(f"Metadata: {metadata}")
        print("--------------------------------------------------")
        print("\n=== End of vault dump ===")

    except VaultError as e:
        print(f"Vault error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
