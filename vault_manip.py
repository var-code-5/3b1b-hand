
import os
from vault.manager import VaultManager

vm = VaultManager()

master = "TestPassword123!@#"
if not master:
    raise SystemExit("Set VAULT_MASTER_PASSWORD first (quote it if it contains '!').")

# Initialize/unlock vault (idempotent)
vm.initialize(master_password=master)

# # Add credential (infinite TTL by default)
# entry = vm.add_credential({
#    "service":"NeoBank",
#    "mobile":"8770762787",
#    "password":"password123",
#    "metadata":{"source": "terminal"},
#    "ttl_seconds":None,  # infinite
# })

# vm.delete_credential("NeoBank")
# vm.delete_credential("NeoBank")
# vm.delete_credential("NeoBank")

print(vm.list_services())


# print("Added:", entry["service"])
# print("expires_at:", entry.get("expires_at"))

# creds = vm.get_credential("NeoBank")
# print("Fetched:", creds)

# fields = vm.get_service_fields("NeoBank")
# print("Fields for NeoBank:", fields)

