import hashlib
import unittest
from pathlib import Path

import bcrypt
from ansible.errors import AnsibleFilterError
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import filter_loader
from ansible.template import Templar, trust_as_template

from filter_plugins.bcrypt_password_hash import bcrypt_password_hash


class BcryptPasswordHashTests(unittest.TestCase):
    def test_default_arguments_in_template(self):
        root = Path(__file__).resolve().parents[1]
        filter_loader.add_directory(str(root / "filter_plugins"))
        template = trust_as_template(
            "{% for username, password in diagnostic_users.items() %}"
            "{{ username }}:{{ password | bcrypt_password_hash }}\n"
            "{% endfor %}"
        )
        templar = Templar(
            loader=DataLoader(),
            variables={
                "inventory_hostname": "tanker",
                "diagnostic_users": {"test": "diagnostic-dummy"},
            },
        )
        expected = "test:$2b$12$fb10549407078744164d6uAi11cKIJQvg0XPT.kK6RmzyzKNexFfq"
        self.assertEqual(templar.template(template).strip(), expected)
        self.assertEqual(templar.template(template).strip(), expected)

    def test_default_salt_depends_on_inventory_host(self):
        first = bcrypt_password_hash({"inventory_hostname": "tanker"}, "test", rounds=4)
        second = bcrypt_password_hash({"inventory_hostname": "other"}, "test", rounds=4)
        self.assertNotEqual(first, second)

    def test_default_salt_requires_inventory_hostname(self):
        with self.assertRaisesRegex(AnsibleFilterError, "inventory_hostname"):
            bcrypt_password_hash({}, "test")

    def test_explicit_arguments_in_template(self):
        root = Path(__file__).resolve().parents[1]
        filter_loader.add_directory(str(root / "filter_plugins"))
        template = trust_as_template(
            "{{ 'test' | bcrypt_password_hash(salt='abcdefghijklmnopqrstu.', rounds=4) }}"
        )
        self.assertEqual(
            Templar(loader=DataLoader()).template(template),
            bcrypt_password_hash({}, "test", "abcdefghijklmnopqrstu.", rounds=4),
        )

    def test_preserves_existing_passlib_hash(self):
        salt = hashlib.sha1(b"tanker").hexdigest()[:22]
        self.assertEqual(
            bcrypt_password_hash({}, "diagnostic-dummy", salt),
            "$2b$12$fb10549407078744164d6uAi11cKIJQvg0XPT.kK6RmzyzKNexFfq",
        )

    def test_passwords_verify_and_hashes_repeat(self):
        salt = "abcdefghijklmnopqrstu."
        for password in ("", "test", "Grüße", "x" * 72):
            with self.subTest(password_length=len(password)):
                hashed = bcrypt_password_hash({}, password, salt, rounds=4)
                self.assertEqual(hashed, bcrypt_password_hash({}, password, salt, rounds=4))
                self.assertTrue(bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii")))

    def test_rejects_passwords_that_would_be_truncated(self):
        for password in ("x" * 73, "ü" * 37):
            with self.subTest(password_length=len(password)):
                with self.assertRaisesRegex(AnsibleFilterError, "72 UTF-8 bytes"):
                    bcrypt_password_hash({}, password, "abcdefghijklmnopqrstu.")

    def test_rejects_invalid_salts(self):
        for salt in ("short", "!" * 22, "ü" * 22):
            with self.subTest(salt=salt):
                with self.assertRaisesRegex(AnsibleFilterError, "22 bcrypt-base64"):
                    bcrypt_password_hash({}, "test", salt)

    def test_rejects_invalid_rounds(self):
        for rounds in (3, 32, "12", True):
            with self.subTest(rounds=rounds):
                with self.assertRaisesRegex(AnsibleFilterError, "rounds"):
                    bcrypt_password_hash({}, "test", "abcdefghijklmnopqrstu.", rounds)
