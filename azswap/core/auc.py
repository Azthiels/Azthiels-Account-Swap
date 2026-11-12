"""".auc" (Azthiels Universal Credentials): encrypted single-account export.

AES-256-GCM with a key derived from a password (PBKDF2-SHA256, 100k iterations).
Decrypted payload: {"service", "alias", "blob_b64", optional "expires_at" (ISO, UTC)}.
"""
import base64
import json
import secrets
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False

AUC_EXT = ".auc"
FORMAT_VERSION = 3
PBKDF2_ITERATIONS = 100_000


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERATIONS)
    return kdf.derive(password.encode("utf-8"))


def encrypt(payload: dict, out_path: Path, password: str) -> None:
    plaintext = json.dumps(payload).encode("utf-8")
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    ciphertext = AESGCM(_derive_key(password, salt)).encrypt(nonce, plaintext, None)
    wrapper = {"v": FORMAT_VERSION, "salt": b64(salt), "nonce": b64(nonce), "ciphertext": b64(ciphertext)}
    out_path.write_text(json.dumps(wrapper), encoding="utf-8")


def decrypt(path: Path, password: str) -> dict:
    """Raises ValueError with a user-readable message on any failure."""
    try:
        wrapper = json.loads(path.read_text(encoding="utf-8"))
        salt, nonce, ciphertext = unb64(wrapper["salt"]), unb64(wrapper["nonce"]), unb64(wrapper["ciphertext"])
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Not a valid {AUC_EXT} file ({e})") from e
    try:
        plaintext = AESGCM(_derive_key(password, salt)).decrypt(nonce, ciphertext, None)
    except Exception as e:  # noqa: BLE001
        raise ValueError("Wrong password or corrupted file") from e
    payload = json.loads(plaintext.decode("utf-8"))
    if not isinstance(payload, dict) or not {"service", "alias", "blob_b64"} <= payload.keys():
        raise ValueError("File is missing account data")
    return payload
