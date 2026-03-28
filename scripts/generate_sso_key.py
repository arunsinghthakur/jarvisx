#!/usr/bin/env python3
"""
Generate SSO encryption key for .env configuration
"""
from cryptography.fernet import Fernet

def generate_key():
    """Generate a new Fernet encryption key"""
    key = Fernet.generate_key()
    return key.decode()

if __name__ == "__main__":
    key = generate_key()
    print("=" * 80)
    print("SSO ENCRYPTION KEY GENERATED")
    print("=" * 80)
    print()
    print("Add this to your .env file:")
    print()
    print(f"SSO_ENCRYPTION_KEY={key}")
    print()
    print("⚠️  IMPORTANT:")
    print("  - Keep this key secure and never commit it to version control")
    print("  - Use the same key across all application instances")
    print("  - Changing the key will invalidate all existing encrypted secrets")
    print("  - Back up this key in a secure location (password manager, vault, etc.)")
    print()
    print("=" * 80)
