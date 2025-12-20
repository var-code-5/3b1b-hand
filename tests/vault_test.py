#!/usr/bin/env python3
"""
Integration Test Suite for Vault Manager
Tests the actual vault/core.py and vault/manager.py implementations.

Run: python -m pytest tests/vault_test.py -v
Or:  python tests/vault_test.py
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vault.core import EncryptedVault, VaultError
from vault.manager import VaultManager


# ============ TEST CONFIGURATION ============

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print a test section header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.END}\n")

def print_pass(text: str):
    """Print a passing test."""
    print(f"{Colors.GREEN}✓ PASS:{Colors.END} {text}")

def print_fail(text: str):
    """Print a failing test."""
    print(f"{Colors.RED}✗ FAIL:{Colors.END} {text}")

def print_info(text: str):
    """Print informational message."""
    print(f"{Colors.YELLOW}ℹ INFO:{Colors.END} {text}")

# ============ VAULT CORE TESTS ============

def test_core_vault_creation():
    """Test EncryptedVault.create() from vault/core.py"""
    print_header("Test 1: Core Vault Creation")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            
            if vault_path.exists():
                print_pass("Vault file created successfully")
            else:
                print_fail("Vault file not created")
                return False
            
            file_size = vault_path.stat().st_size
            mode = vault_path.stat().st_mode
            perms = oct(mode)[-3:]
            print_info(f"File size: {file_size} bytes, Permissions: {perms}")
            
            if perms == "600":
                print_pass("File permissions set to 600 (owner-only)")
            else:
                print_fail(f"File permissions incorrect: {perms}")
                return False
            
            if not vault.is_locked():
                print_pass("Vault is unlocked after creation")
            else:
                print_fail("Vault is locked after creation")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during creation: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_core_add_credentials():
    """Test EncryptedVault.add_credential() from vault/core.py"""
    print_header("Test 2: Core Add Credentials")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            
            # Add multiple credentials
            test_creds = [
                ("openai_api", "user@example.com", "sk-1234567890abcdef", {"purpose": "gpt-4"}),
                ("github_token", "github_user", "ghp_abcdef1234567890", None),
                ("aws_key", "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", None),
            ]
            
            for service, username, password, metadata in test_creds:
                entry = vault.add_credential(service, username, password, metadata)
                if entry["service"] == service:
                    print_pass(f"Added credential: {service}")
                else:
                    print_fail(f"Failed to add credential: {service}")
                    return False
            
            services = vault.list_services()
            if len(services) == 3:
                print_pass(f"All 3 credentials added. Services: {', '.join(services)}")
            else:
                print_fail(f"Expected 3 credentials, got {len(services)}")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during add: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_core_retrieve_credentials():
    """Test EncryptedVault.get_credential() from vault/core.py"""
    print_header("Test 3: Core Retrieve Credentials")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            
            # Add a credential
            vault.add_credential("github_token", "octocat", "ghp_secret123", {"repo": "myproject"})
            
            # Retrieve it
            entry = vault.get_credential("github_token")
            if entry:
                print_pass(f"Retrieved credential: {entry['service']}")
                if entry["username"] == "octocat":
                    print_pass(f"Username matches: {entry['username']}")
                else:
                    print_fail(f"Username mismatch: {entry['username']}")
                    return False
                
                if entry["password"] == "ghp_secret123":
                    print_pass("Password matches")
                else:
                    print_fail("Password mismatch")
                    return False
                
                if entry["metadata"].get("repo") == "myproject":
                    print_pass("Metadata retrieved correctly")
                else:
                    print_fail("Metadata mismatch")
                    return False
            else:
                print_fail("Could not retrieve credential")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during retrieval: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_core_encryption_strength():
    """Test that vault is actually encrypted (no plaintext in file)"""
    print_header("Test 4: Core Encryption Verification")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        plaintext_data = "SuperSecretAPIKey123456789"
        
        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            vault.add_credential("secret_service", "user", plaintext_data)
            vault.lock()
            
            # Read raw file
            with open(vault_path, 'rb') as f:
                encrypted_bytes = f.read()
            
            # Check if plaintext is in file
            if plaintext_data.encode() in encrypted_bytes:
                print_fail("SECURITY ISSUE: Plaintext data found in vault file!")
                return False
            else:
                print_pass("Plaintext data NOT found in vault file (encrypted)")
            
            print_info(f"Vault file size: {len(encrypted_bytes)} bytes")
            print_info(f"Salt size: 16 bytes, Nonce size: 12 bytes")
            
            # Try to read with wrong password
            vault_wrong = EncryptedVault(vault_path, "WrongPassword!")
            try:
                vault_wrong.unlock()
                print_fail("SECURITY ISSUE: Decrypted with wrong password!")
                return False
            except VaultError:
                print_pass("Wrong password rejected (authentication working)")
            
            return True
        except Exception as e:
            print_fail(f"Exception during encryption test: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_core_lock_unlock():
    """Test EncryptedVault lock/unlock cycle"""
    print_header("Test 5: Core Lock/Unlock Cycle")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            vault.add_credential("github", "user", "token123")
            
            print_pass("Vault created and credential added")
            
            # Lock vault
            vault.lock()
            if vault.is_locked():
                print_pass("Vault locked successfully")
            else:
                print_fail("Vault not locked")
                return False
            
            # Try to access while locked
            try:
                vault.get_credential("github")
                print_fail("SECURITY ISSUE: Accessed credential while locked!")
                return False
            except VaultError:
                print_pass("Access to locked vault denied")
            
            # Unlock vault
            vault.unlock()
            if not vault.is_locked():
                print_pass("Vault unlocked successfully")
            else:
                print_fail("Vault not unlocked")
                return False
            
            # Access credential again
            entry = vault.get_credential("github")
            if entry:
                print_pass("Credential accessible after unlock")
            else:
                print_fail("Credential not found after unlock")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during lock/unlock: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_core_persistence():
    """Test vault persistence across sessions"""
    print_header("Test 6: Core Persistence Across Sessions")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            # Session 1: Create and add
            vault1 = EncryptedVault(vault_path, master_pass)
            vault1.create()
            vault1.add_credential("openai", "user", "sk-key123")
            vault1.add_credential("github", "user", "ghp-token")
            vault1.lock()
            print_pass("Session 1: Created vault and added 2 credentials")
            
            # Session 2: Load and verify
            vault2 = EncryptedVault(vault_path, master_pass)
            vault2.unlock()
            
            services = vault2.list_services()
            if len(services) == 2:
                print_pass(f"Session 2: Loaded {len(services)} credentials")
            else:
                print_fail(f"Expected 2 credentials, got {len(services)}")
                return False
            
            # Session 3: Modify
            vault2.add_credential("aws", "user", "AKIA...")
            services = vault2.list_services()
            if len(services) == 3:
                print_pass("Session 2: Added 1 more credential")
            else:
                print_fail("Failed to add credential in session 2")
                return False
            
            vault2.lock()
            
            # Session 4: Verify modifications persisted
            vault3 = EncryptedVault(vault_path, master_pass)
            vault3.unlock()
            services = vault3.list_services()
            if len(services) == 3 and "aws" in services:
                print_pass("Session 3: All modifications persisted")
            else:
                print_fail("Modifications not persisted")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during persistence test: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_core_delete_credential():
    """Test EncryptedVault.delete_credential()"""
    print_header("Test 7: Core Delete Credentials")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            
            # Add multiple
            vault.add_credential("service1", "user1", "pass1")
            vault.add_credential("service2", "user2", "pass2")
            vault.add_credential("service3", "user3", "pass3")
            
            if len(vault.list_services()) == 3:
                print_pass("Added 3 credentials")
            else:
                print_fail("Failed to add credentials")
                return False
            
            # Delete one
            deleted = vault.delete_credential("service2")
            if deleted:
                print_pass("Deleted credential: service2")
            else:
                print_fail("Failed to delete credential")
                return False
            
            # Verify it's gone
            services = vault.list_services()
            if len(services) == 2 and "service2" not in services:
                print_pass(f"Remaining services: {', '.join(services)}")
            else:
                print_fail("Delete did not work correctly")
                return False
            
            # Verify persistent
            vault.lock()
            vault.unlock()
            services = vault.list_services()
            if len(services) == 2 and "service2" not in services:
                print_pass("Deletion persisted after lock/unlock")
            else:
                print_fail("Deletion not persisted")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during delete test: {e}")
            import traceback
            traceback.print_exc()
            return False

# ============ VAULT MANAGER TESTS ============

def test_manager_initialization():
    """Test VaultManager.initialize() with custom vault path"""
    print_header("Test 8: Manager Initialization")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            # Create a vault instance directly
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            
            # Create manager and initialize with same vault
            manager = VaultManager()
            manager._vault = vault  # Inject the vault
            
            if manager.is_locked() == False:
                print_pass("Manager initialized with unlocked vault")
            else:
                print_fail("Manager vault is locked after init")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during manager init: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_manager_add_credential():
    """Test VaultManager.add_credential() via manager interface"""
    print_header("Test 9: Manager Add Credential")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            # Setup vault
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            
            # Setup manager
            manager = VaultManager()
            manager._vault = vault
            
            # Add via manager
            entry = manager.add_credential("openai", "user@example.com", "sk-secret123")
            
            if entry["service"] == "openai":
                print_pass("Added credential via manager")
            else:
                print_fail("Failed to add credential via manager")
                return False
            
            # Verify via manager
            services = manager.list_services()
            if "openai" in services:
                print_pass("Credential listed via manager")
            else:
                print_fail("Credential not found in list")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during manager add: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_manager_get_credential():
    """Test VaultManager.get_credential() and display retrieved keys on CLI."""
    print_header("Test 10: Manager Get Credential (Show Secrets)")

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"

        try:
            # Setup
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            vault.add_credential(
                "github",
                "octocat",
                "ghp_secret",
                {"repo": "test-repo", "note": "demo secret for test"},
            )

            manager = VaultManager()
            manager._vault = vault

            # Get via manager
            entry = manager.get_credential("github")

            if not entry:
                print_fail("Failed to retrieve credential via manager")
                return False

            # Normal test assertions
            if entry["username"] == "octocat":
                print_pass("Retrieved credential via manager (username matches)")
            else:
                print_fail(f"Username mismatch: {entry['username']}")
                return False

            if entry["password"] == "ghp_secret":
                print_pass("Password matches expected value")
            else:
                print_fail("Password mismatch")
                return False

            # EXTRA: print the retrieved secret clearly on CLI
            print_info("=== Retrieved credential (for manual inspection) ===")
            print_info(f"Service : {entry['service']}")
            print_info(f"Username: {entry['username']}")
            print_info(f"Password: {entry['password']}")
            if entry.get("metadata"):
                print_info(f"Metadata: {json.dumps(entry['metadata'], indent=2)}")
            print_info("=== End of credential dump ===")

            return True

        except Exception as e:
            print_fail(f"Exception during manager get: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_manager_lock_unlock():
    """Test VaultManager.lock() and is_locked()"""
    print_header("Test 11: Manager Lock/Unlock")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"
        
        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()
            
            manager = VaultManager()
            manager._vault = vault
            
            if not manager.is_locked():
                print_pass("Manager shows vault is unlocked")
            else:
                print_fail("Manager shows vault is locked")
                return False
            
            manager.lock()
            
            if manager.is_locked():
                print_pass("Manager locked vault successfully")
            else:
                print_fail("Manager failed to lock vault")
                return False
            
            return True
        except Exception as e:
            print_fail(f"Exception during manager lock/unlock: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_core_ttl_expires_quickly():
    """Create a short-lived secret (OTP-like) and verify it expires."""
    print_header("Test 12: Core TTL Expiration (OTP 2s)")

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"

        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()

            # Store OTP that expires quickly
            vault.add_credential(
                "otp_demo",
                "user",
                "123456",
                {"type": "otp"},
                ttl_seconds=2,
            )

            entry_now = vault.get_credential("otp_demo")
            if not entry_now:
                print_fail("OTP should be available immediately but was not found")
                return False
            print_pass("OTP available immediately after insert")

            print_info("Sleeping 3 seconds to ensure TTL expiry...")
            time.sleep(3)

            entry_later = vault.get_credential("otp_demo")
            if entry_later is None:
                print_pass("OTP expired and is no longer retrievable")
            else:
                print_fail("OTP should have expired but was still retrievable")
                return False

            # Optional: if your core purges on read, it should not be listed anymore
            services = vault.list_services()
            if "otp_demo" not in services:
                print_pass("Expired OTP not present in list_services()")
            else:
                print_fail("Expired OTP still present in list_services()")
                return False

            return True

        except TypeError as e:
            print_fail(f"Your core.add_credential signature likely doesn't support ttl_seconds yet: {e}")
            return False
        except Exception as e:
            print_fail(f"Exception during TTL test: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_core_ttl_infinite_when_missing():
    """If ttl_seconds is not provided, credential should behave as infinite TTL."""
    print_header("Test 13: Core TTL Infinite When Missing")

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"

        try:
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()

            # No ttl_seconds => infinite
            vault.add_credential(
                "infinite_demo",
                "user",
                "permanent_secret",
                {"note": "no ttl set"},
            )

            print_info("Sleeping 2 seconds; infinite credential should still exist...")
            time.sleep(2)

            entry = vault.get_credential("infinite_demo")
            if entry and entry["password"] == "permanent_secret":
                print_pass("Credential persisted without TTL (infinite TTL behavior)")
                return True

            print_fail("Credential missing after short wait; infinite TTL behavior broken")
            return False

        except TypeError as e:
            # This one should still pass even if ttl_seconds not implemented (because it doesn't use ttl_seconds),
            # but keeping the handler here for clarity.
            print_fail(f"Unexpected TypeError: {e}")
            return False
        except Exception as e:
            print_fail(f"Exception during infinite TTL test: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_manager_ttl_passthrough_expires():
    """Verify VaultManager passes ttl_seconds into core and expiry is enforced via manager.get_credential."""
    print_header("Test 14: Manager TTL Passthrough (Expires)")

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault.enc"
        master_pass = "TestPassword123!@#"

        try:
            # Use core directly to control the temp vault path
            vault = EncryptedVault(vault_path, master_pass)
            vault.create()

            manager = VaultManager()
            manager._vault = vault  # inject test vault

            manager.add_credential(
                "temp_token",
                "user",
                "token_value",
                {"note": "short ttl"},
                ttl_seconds=1,
            )
            print_pass("Added TTL credential via manager")

            # Immediately should work
            entry_now = manager.get_credential("temp_token")
            if entry_now:
                print_pass("Manager retrieved credential before expiry")
            else:
                print_fail("Manager could not retrieve credential before expiry")
                return False

            print_info("Sleeping 2 seconds to ensure expiry...")
            time.sleep(2)

            entry_later = manager.get_credential("temp_token")
            if entry_later is None:
                print_pass("Manager returned None after expiry (TTL enforced)")
                return True

            print_fail("Manager still returned credential after expiry")
            return False

        except TypeError as e:
            print_fail(f"Your manager.add_credential likely doesn't accept ttl_seconds yet: {e}")
            return False
        except Exception as e:
            print_fail(f"Exception during manager TTL test: {e}")
            import traceback
            traceback.print_exc()
            return False


# ============ MAIN ============

def run_all_tests():
    """Run all tests and report results."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║    VAULT CORE & MANAGER INTEGRATION TEST SUITE            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    tests = [
        # Core tests
        test_core_vault_creation,
        test_core_add_credentials,
        test_core_retrieve_credentials,
        test_core_encryption_strength,
        test_core_lock_unlock,
        test_core_persistence,
        test_core_delete_credential,
        # Manager tests
        test_manager_initialization,
        test_manager_add_credential,
        test_manager_get_credential,
        test_manager_lock_unlock,
        test_core_ttl_expires_quickly,
        test_core_ttl_infinite_when_missing,
        test_manager_ttl_passthrough_expires,

    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print_fail(f"Unhandled exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{status}: {name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} passed{Colors.END}\n")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)