"""Generate portable bcrypt hashes; requires the controller's bcrypt package."""

import hashlib
import re

from ansible.errors import AnsibleFilterError
from jinja2 import pass_context


@pass_context
def bcrypt_password_hash(context, password, salt=None, rounds=12):
    """Default to a stable inventory-host salt and bcrypt cost 12."""
    try:
        import bcrypt
    except ImportError as exc:
        raise AnsibleFilterError(
            "bcrypt_password_hash requires the Python bcrypt package on the controller"
        ) from exc

    if salt is None:
        hostname = context.get("inventory_hostname")
        if not isinstance(hostname, str) or not hostname:
            raise AnsibleFilterError(
                "bcrypt_password_hash requires inventory_hostname when salt is omitted"
            )
        salt = hashlib.sha1(hostname.encode("utf-8")).hexdigest()[:22]

    if not isinstance(salt, str) or not re.fullmatch(r"[./A-Za-z0-9]{22}", salt):
        raise AnsibleFilterError("bcrypt salt must contain 22 bcrypt-base64 characters")
    if type(rounds) is not int or not 4 <= rounds <= 31:
        raise AnsibleFilterError("bcrypt rounds must be an integer between 4 and 31")
    if not isinstance(password, str):
        raise AnsibleFilterError("bcrypt password must be a string")

    secret = password.encode("utf-8")
    # Older bcrypt versions silently truncate passwords beyond 72 bytes.
    if len(secret) > 72:
        raise AnsibleFilterError("bcrypt passwords must not exceed 72 UTF-8 bytes")

    # Clear unused padding bits, matching Passlib's historical salt handling.
    alphabet = "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    salt = salt[:-1] + alphabet[alphabet.index(salt[-1]) & 0x30]
    setting = f"$2b${rounds:02d}${salt}".encode("ascii")
    return bcrypt.hashpw(secret, setting).decode("ascii")


@pass_context
def htpasswd_users(context, users, salt=None, rounds=12):
    """Convert a user/password mapping to portable htpasswd entries."""
    return [
        f"{user}:{bcrypt_password_hash(context, password, salt, rounds)}"
        for user, password in users.items()
    ]


class FilterModule:
    def filters(self):
        return {
            "bcrypt_password_hash": bcrypt_password_hash,
            "htpasswd_users": htpasswd_users,
        }
