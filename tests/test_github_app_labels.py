import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "github_app_labels",
    ROOT / "templates/hermes-agent/hermes/templates/app/profiles/developer/scripts/github_app_labels.py",
)
labels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(labels)
WEBHOOK_SPEC = importlib.util.spec_from_file_location(
    "github_webhook",
    ROOT / "templates/hermes-agent/hermes/templates/app/profiles/developer/scripts/github_webhook.py",
)
webhook = importlib.util.module_from_spec(WEBHOOK_SPEC)
with patch.dict(sys.modules, github_app_labels=labels):
    WEBHOOK_SPEC.loader.exec_module(webhook)


class GitHubWebhookTests(unittest.TestCase):
    def test_dispatch_tries_handlers_until_one_handles_the_event(self):
        payload = {"action": "custom"}
        result = {"__hermes_ignore__": True}
        first = Mock(return_value=None)
        second = Mock(return_value=result)
        third = Mock()
        with patch.object(webhook, "HANDLERS", (first, second, third)):
            self.assertIs(webhook.dispatch(payload), result)
        first.assert_called_once_with(payload)
        second.assert_called_once_with(payload)
        third.assert_not_called()

    def test_handler_can_transform_payload_for_skill_dispatch(self):
        transformed = {"action": "custom", "context": "verified"}
        with patch.object(webhook, "HANDLERS", (Mock(return_value=transformed),)):
            self.assertIs(webhook.dispatch({"action": "custom"}), transformed)

    def test_each_profile_entrypoint_passes_unhandled_events_to_skill(self):
        payload = {"action": "submitted", "installation": {"id": 123}, "review": {"id": 456}}
        for profile in ("developer", "reviewer"):
            with self.subTest(profile=profile):
                script = ROOT / f"templates/hermes-agent/hermes/templates/app/profiles/{profile}/scripts/github_webhook.py"
                result = subprocess.run(
                    [sys.executable, str(script)], input=json.dumps(payload),
                    capture_output=True, text=True, check=True, timeout=10,
                )
                self.assertEqual(json.loads(result.stdout), payload)


class GitHubAppLabelsTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        Path(self.home.name, "config.yaml").write_text(
            "github_app:\n  installation_ids:\n    agross: 123\n"
        )
        env = patch.dict(os.environ, HERMES_HOME=self.home.name)
        env.start()
        self.addCleanup(env.stop)
        self.event = {
            "action": "created",
            "installation": {"id": 123, "account": {"login": "agross"}},
            "repositories": [{"full_name": "agross/first"}],
        }

    @patch.object(labels, "gh_app")
    def test_initial_installation_provisions_all_labels_and_stops_dispatch(self, gh):
        self.event["repositories"].append({"full_name": "agross/second"})
        self.assertEqual(webhook.dispatch(self.event), {"__hermes_ignore__": True})
        self.assertEqual(gh.call_count, 8)
        expected = {
            "implementing": ("29e884", "Agent implementation is in progress."),
            "in-review": ("ededed", "Agent review and any required repairs are in progress."),
            "needs-human": ("bf3c05", "Human input, a decision, or final approval is required."),
            "ready-for-agent": ("aa46ed", "Authorized and ready for the developer agent to work on."),
        }
        for repo in ("agross/first", "agross/second"):
            for name, (color, description) in expected.items():
                gh.assert_any_call(
                    repo, "label", "create", name, "--repo", repo,
                    "--color", color, "--description", description, "--force",
                )

    @patch.object(labels, "gh_app")
    def test_repository_additions_ignore_removed_repositories_and_deduplicate(self, gh):
        self.event.update(
            action="added",
            repositories_added=[{"full_name": "agross/new"}] * 2,
            repositories_removed=[{"full_name": "agross/removed"}],
        )
        labels.provision(self.event)
        self.assertEqual(gh.call_count, 4)
        self.assertTrue(all(call.args[0] == "agross/new" for call in gh.call_args_list))

    @patch.object(labels, "gh_app", return_value="agross/first\nagross/second\n")
    def test_all_repository_installations_use_paginated_api(self, gh):
        self.event["installation"]["repository_selection"] = "all"
        labels.provision(self.event)
        self.assertEqual(gh.call_count, 9)
        gh.assert_any_call(
            "agross/_", "api", "--paginate", "installation/repositories",
            "--jq", ".repositories[].full_name",
        )

    @patch.object(labels, "gh_app", return_value="")
    def test_missing_initial_repository_list_is_enumerated(self, gh):
        del self.event["repositories"]
        self.assertEqual(labels.provision(self.event), {"__hermes_ignore__": True})
        self.assertEqual(gh.call_count, 1)

    @patch.object(labels, "gh_app")
    def test_normal_events_pass_through_without_commands(self, gh):
        for action in ("labeled", "submitted", "synchronize", "created"):
            payload = {"action": action, "installation": {"id": 123}, "issue": {"number": 1}}
            self.assertIs(webhook.dispatch(payload), payload)
        gh.assert_not_called()

    @patch.object(labels, "gh_app")
    def test_rejects_mismatched_installation_or_repository_before_writes(self, gh):
        self.event["installation"]["id"] = 456
        with self.assertRaises(ValueError):
            labels.provision(self.event)
        self.event["installation"]["id"] = 123
        for name in ("another/repo", "agross/repo;echo injected", "--help"):
            self.event["repositories"].append({"full_name": name})
            with self.assertRaises(ValueError):
                labels.provision(self.event)
            self.event["repositories"].pop()
        gh.assert_not_called()

    @patch.object(labels, "gh_app", side_effect=subprocess.CalledProcessError(1, ["gh-app"]))
    def test_failure_does_not_emit_agent_payload(self, gh):
        import io

        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(self.event))), patch("sys.stdout", output), patch("sys.stderr", io.StringIO()):
            self.assertEqual(webhook.main(), 1)
        self.assertEqual(output.getvalue(), "")

    def test_wrapper_keeps_repository_and_cli_arguments_separate(self):
        with patch.object(labels.subprocess, "run") as run:
            labels.gh_app("agross/repo", "label", "create", "in-review", "--repo", "agross/repo")
        self.assertEqual(run.call_args.args[0], [
            "gh-app", "--repo", "agross/repo", "--", "label", "create",
            "in-review", "--repo", "agross/repo",
        ])
        self.assertTrue(run.call_args.kwargs["check"])

    def test_routes_render_with_installation_events_and_script_for_both_profiles(self):
        profile = {
            name: {"github": {"webhook": {"secret": "test-secret"}, "app": {"installation_ids": {"agross": 123}}}}
            for name in ("developer", "reviewer")
        }
        variables = {
            "ansible_managed": "test", "hermes_profile": profile,
            "hermes_api_server_enabled": False, "hermes_webhooks_enabled": True,
            "hermes_api_server_cors_origins": [], "hermes_approvals_mode": "off",
            "hermes_approvals_cron_mode": "off", "hermes_approvals_unattended_mode": "off",
            "hermes_timezone": "Europe/Berlin", "hermes_domain": "hermes.example.test",
            "hostvars": {"proxy-home": {"interfaces": {"lan": {"ip4": {"address": "192.0.2.1"}}}}},
        }
        template = (ROOT / "templates/hermes-agent/hermes/templates/app/config.yaml.j2").read_text()
        rendered = Templar(loader=DataLoader(), variables=variables).template(trust_as_template(template))
        config = yaml.safe_load(rendered)["platforms"]["webhook"]["extra"]
        self.assertEqual(config["script_timeout_seconds"], 300)
        for name in ("developer", "reviewer"):
            route = config["routes"][f"{name}-github"]
            self.assertEqual(route["profile"], name)
            self.assertEqual(route["script"], "github_webhook.py")
            self.assertIn("installation", route["events"])
            self.assertIn("installation_repositories", route["events"])
            self.assertEqual(route["filters"][0], {"field": "installation.id", "in": [123]})


if __name__ == "__main__":
    unittest.main()
