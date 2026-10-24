import unittest
from pathlib import Path

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import filter_loader
from ansible.template import Templar, trust_as_template

from filter_plugins.bcrypt_password_hash import htpasswd_users


class HtpasswdUsersTests(unittest.TestCase):
    def test_empty_users(self):
        self.assertEqual(htpasswd_users({}, {}), [])

    def test_multiple_users_keep_mapping_order(self):
        entries = htpasswd_users(
            {},
            {"first": "test", "second": "test"}, "fb10549407078744164d61", rounds=4
        )
        self.assertEqual([entry.split(":")[0] for entry in entries], ["first", "second"])
        self.assertEqual(entries[0].split(":")[1], entries[1].split(":")[1])

    def test_templates_render_without_precomputed_facts(self):
        root = Path(__file__).resolve().parents[1]
        filter_loader.add_directory(str(root / "filter_plugins"))
        templates = (
            ("templates/feedr/traefik.yaml.j2", "feedr", "feedr-auth"),
            ("templates/nextcloud/traefik.yaml.j2", "nextcloud", "nextcloud-kibana-auth"),
            ("roles/traefik/templates/conf.d/traefik/dashboard.yaml.j2", "traefik", "dashboard-auth"),
            ("roles/nextcloud/templates/docker-compose.yaml.j2", "nextcloud", None),
        )
        expected = ["test:$2b$12$fb10549407078744164d6uAi11cKIJQvg0XPT.kK6RmzyzKNexFfq"]
        for users in ({"test": "diagnostic-dummy"}, {}, None):
            for path, role, middleware in templates:
                with self.subTest(path=path, users_defined=users is not None, users_empty=not users):
                    variables = {
                        "inventory_hostname": "tanker",
                        "ansible_managed": "Ansible managed",
                        "ansible_role_name": role,
                        "ansible_facts": {"hostname": "tanker", "virtualization_tech_guest": []},
                        "network": {"domain": "example.test", "ip4": "192.0.2.0/24", "ip6": "2001:db8::/64"},
                        "interfaces": {"lan": {"ip4": {"address": "192.0.2.1"}}},
                        "hostvars": {"proxy-home": {"interfaces": {"lan": {"ip4": {"address": "192.0.2.2"}}}}},
                        "feedr_domain": "feedr.example.test",
                        "nextcloud_domain": "nextcloud.example.test",
                        "nextcloud_version": "test",
                        "nextcloud_upgrade_timeout": "3m",
                        "nextcloud_mcp_client_list": [],
                        "nextcloud_mcp_management_client_list": [],
                        "traefik_generate_wildcard_cert": True,
                    }
                    for name in (
                        "oidc_client_id", "oidc_client_secret", "token_encryption_key",
                        "qdrant_admin_api_key", "qdrant_readonly_api_key", "webhook_secret",
                    ):
                        variables[f"nextcloud_mcp_{name}"] = "dummy"
                    if users is not None:
                        variables.update(
                            feedr_users=users,
                            nextcloud_kibana_users=users,
                            traefik_users={"dashboard": users},
                        )
                    rendered = Templar(loader=DataLoader(), variables=variables).template(
                        trust_as_template((root / path).read_text()),
                        overrides={"lstrip_blocks": True},
                    )
                    document = yaml.safe_load(rendered)
                    entries = expected if users else []
                    if middleware:
                        auth = document["http"]["middlewares"][middleware]
                        self.assertEqual(auth.get("basicauth", auth.get("basicAuth"))["users"], entries)
                    else:
                        labels = document["services"]["kibana"]["labels"]
                        self.assertEqual(
                            labels["traefik.http.middlewares.nextcloud-kibana-auth.basicauth.users"],
                            ",".join(entries).replace("$", "$$"),
                        )
