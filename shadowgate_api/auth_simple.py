# shadowgate_api/auth_simple.py
import hashlib
import secrets

# returns "salt$hexhash"
def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)  # 32 hex chars = 16 bytes
    h = hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()
    return f"{salt}${h}"

def verify_password(pw: str, stored: str) -> bool:
    try:
        salt, good = stored.split("$", 1)
    except ValueError:
        return False
    h = hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()
    # constant-time compare
    return secrets.compare_digest(h, good)
