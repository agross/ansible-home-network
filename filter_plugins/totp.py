"""Generate RFC 6238 time-based one-time passwords."""

import base64
import binascii
import hashlib
import hmac
import struct
import time

from ansible.errors import AnsibleFilterError


def _decode_secret(secret):
    if not isinstance(secret, str) or not secret.strip():
        raise AnsibleFilterError("TOTP secret must be a non-empty Base32 string")

    normalized_secret = "".join(secret.split()).upper()
    padded_secret = normalized_secret + "=" * (-len(normalized_secret) % 8)

    try:
        return base64.b32decode(padded_secret, casefold=True)
    except (binascii.Error, ValueError) as error:
        raise AnsibleFilterError("TOTP secret must be valid Base32") from error


def _timestamp(for_time):
    try:
        timestamp = time.time() if for_time is None else float(for_time)
    except (TypeError, ValueError) as error:
        raise AnsibleFilterError("TOTP timestamp must be numeric") from error

    if timestamp < 0:
        raise AnsibleFilterError("TOTP timestamp must not be negative")

    return timestamp


def _hotp(key, counter):
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary_code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{binary_code % 1_000_000:06d}"


def totp(secret, for_time=None):
    """Return current six-digit, SHA-1, 30-second TOTP for Base32 secret."""
    key = _decode_secret(secret)
    counter = int(_timestamp(for_time) // 30)
    return _hotp(key, counter)


class FilterModule(object):
    """Expose TOTP filter to Ansible."""

    def filters(self):
        return {
            "totp": totp,
        }
