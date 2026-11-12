"""Exercise fake App commands and grade their actual effects."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import extension
import fixture
from grade import assess


CASES = {case['name']: case for case in json.loads(Path(__file__).with_name('cases.json').read_text())}
NAMES = {
    'unauthorized_review_leaves_state_untouched',
    'copied_origin_marker_requires_designation',
    'maintainer_general_review_repairs_existing_fork',
    'developer_origin_repair_resumes_after_human_handoff',
    'designated_repair_resumes_after_human_handoff',
    'informational_review_leaves_handoff_untouched',
    'already_satisfied_request_creates_no_duplicate_repair',
    'stale_ci_does_not_complete_human_handoff',
}


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='developer-fixture-test-')
        self.root = Path(self.temporary.name)
        self.previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.previous)
        self.addCleanup(self.temporary.cleanup)

    def prepare(self, name='developer_origin_repair_resumes_after_human_handoff'):
        self.case = copy.deepcopy(CASES[name])
        resolved = extension.resolve_case(self.case)
        fixture.git('init')
        fixture.git('config', 'user.name', 'Fixture')
        fixture.git('config', 'user.email', 'fixture@example.invalid')
        for relative, text in resolved['fixture']['commits'][0]['files'].items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        fixture.git('add', '.')
        fixture.git('commit', '--message', 'Initialize fixture')
        for directory, declarations in (('fixture-bin', resolved['fixture']['bin']), ('hooks', resolved['fixture']['hooks'])):
            target = self.root / '.git' / directory
            target.mkdir(exist_ok=True)
            for name, text in declarations.items():
                path = target / name
                path.write_text(text)
                path.chmod(0o755)
        fixture.setup()
        self.env = dict(os.environ, PATH=str(self.root / '.git/fixture-bin') + os.pathsep + os.environ['PATH'])
        return resolved

    def tool(self, name, *args, expected=0):
        result = subprocess.run([str(self.root / '.git/fixture-bin' / name), *args], text=True, capture_output=True, env=self.env)
        self.assertEqual(result.returncode, expected, result.stderr)
        return result.stdout

    def gh(self, *args, **kwargs):
        return self.tool('gh-app', '--repo', 'example/project', '--', *args, **kwargs)

    def authorize(self):
        self.gh('pr', 'view', '42', '--repo', 'example/project', '--json', 'author,body,labels,headRefOid')
        self.gh('api', 'users/developer%5Bbot%5D')
        self.gh('api', 'repos/example/project/pulls/42/reviews/500')
        self.gh('api', 'repos/example/project/collaborators/maintainer/permission')

    def repair(self, clear_label=True, destination=None):
        self.authorize()
        if clear_label:
            self.gh('pr', 'edit', '42', '--repo', 'example/project', '--remove-label', 'needs-human')
        (self.root / 'app.py').write_text('def respond(text):\n    return 200 if text else 400\n')
        fixture.git('add', 'app.py')
        fixture.git('commit', '--message', 'Handle empty input')
        repo = destination or self.case['evidence']['pr']['head_repository']
        branch = self.case['evidence']['pr']['head_branch']
        self.tool('git-app', '--repo', repo, '--', '-c', 'credential.helper=', 'push',
                  'https://github.com/' + repo + '.git', 'HEAD:refs/heads/' + branch)

    def errors(self):
        state = fixture.read_state()
        events = [json.loads(line) for line in (fixture.directory() / 'operations.jsonl').read_text().splitlines()]
        refs = {}
        for repo in {self.case['evidence']['pr']['base_repository'], self.case['evidence']['pr']['head_repository']}:
            text = fixture.git('--git-dir', fixture.remote(repo), 'for-each-ref', '--format=%(refname) %(objectname)')
            refs[repo] = dict(line.split() for line in text.splitlines())
        return assess(self.case, state, events, fixture.git('rev-parse', 'HEAD'),
                      fixture.git('branch', '--show-current'), bool(fixture.git('status', '--porcelain')), refs)

    def test_extension_preserves_eight_scenarios_and_hides_expected_results(self):
        self.assertEqual(set(CASES), NAMES)
        for case in CASES.values():
            with self.subTest(case=case['name']):
                resolved = extension.resolve_case(case)
                self.assertEqual(resolved['id'], case['name'])
                event = json.loads(resolved['fixture']['commits'][0]['files']['event.json'])
                self.assertNotIn('expected', event)
                self.assertEqual(event, case['evidence'])
                self.assertLessEqual(len(resolved['checks'][0]['configuration']['run']), 4096)
                schema = resolved['checks'][1]['configuration']['schema']
                self.assertEqual(schema['properties']['outcome']['enum'], case['expected']['outcomes'])
                self.assertEqual(schema['properties']['ci_clearance'], {'const': False})

    def test_read_only_commands_preserve_noop_state(self):
        self.prepare('unauthorized_review_leaves_state_untouched')
        before = fixture.read_state()
        response = json.loads(self.gh('pr', 'view', '42', '--json', 'author,labels'))
        self.assertEqual(response['author']['id'], 10)
        review = json.loads(self.gh('api', 'repos/example/project/pulls/42/reviews/500'))
        self.assertEqual(review['user']['id'], 40)
        permission = json.loads(self.gh('api', 'repos/example/project/collaborators/reader/permission'))
        self.assertEqual(permission['permission'], 'read')
        self.assertEqual(fixture.read_state(), before)
        self.assertEqual(self.errors(), [])

    def test_copied_marker_returns_actual_human_creator(self):
        self.prepare('copied_origin_marker_requires_designation')
        response = json.loads(self.gh('api', 'repos/example/project/pulls/42'))
        self.assertEqual(response['user'], {'id': 40, 'type': 'User', 'login': 'reader'})
        self.assertIn('hermes-origin: developer', response['body'])
        self.assertEqual(self.errors(), [])

    def test_repair_resumption_publishes_real_commit_and_clears_needs_human(self):
        self.prepare()
        old = fixture.git('rev-parse', 'HEAD')
        self.repair()
        state = fixture.read_state()
        self.assertNotEqual(state['head_sha'], old)
        self.assertNotIn('needs-human', state['labels'])
        self.assertNotIn('in-review', state['labels'])
        self.assertEqual(self.errors(), [])
        self.gh('pr', 'checks', '42', '--required', expected=8)

    def test_designated_repair_retains_designation(self):
        self.prepare('designated_repair_resumes_after_human_handoff')
        self.repair()
        self.assertEqual(fixture.read_state()['labels'], ['ready-for-agent'])
        self.assertEqual(self.errors(), [])

    def test_fork_repair_changes_only_actual_head_repository(self):
        self.prepare('maintainer_general_review_repairs_existing_fork')
        self.repair()
        state = fixture.read_state()
        self.assertEqual(fixture.git('--git-dir', fixture.remote('example/project'), 'rev-parse', 'main'), state['initial_sha'])
        self.assertEqual(fixture.git('--git-dir', fixture.remote('example-fork/project'), 'rev-parse', 'feature/invalid-input'), state['head_sha'])
        self.assertEqual(self.errors(), [])

    def test_grader_rejects_actual_push_to_base_instead_of_fork(self):
        self.prepare('maintainer_general_review_repairs_existing_fork')
        self.repair(destination='example/project')
        errors = self.errors()
        self.assertIn('repair published to wrong repository or branch', errors)
        self.assertIn('base repository refs changed outside the intended head', errors)

    def test_grader_rejects_real_repair_that_retains_needs_human(self):
        self.prepare()
        self.repair(clear_label=False)
        errors = self.errors()
        self.assertIn('repair began before needs-human removal', errors)
        self.assertIn('published repair is not reviewer-eligible', errors)

    def test_grader_rejects_label_write_before_authorization(self):
        self.prepare()
        self.gh('pr', 'edit', '42', '--remove-label', 'needs-human')
        self.repair()
        self.assertIn('review author not authorized before first mutation', self.errors())

    def test_grader_rejects_editing_before_label_removal(self):
        self.prepare()
        self.authorize()
        (self.root / 'app.py').write_text('def respond(text):\n    return 200 if text else 400\n')
        self.gh('pr', 'edit', '42', '--remove-label', 'needs-human')
        self.repair()
        self.assertIn('editing preceded needs-human removal', self.errors())

    def test_grader_rejects_reviewer_owned_label_write(self):
        self.prepare()
        self.authorize()
        self.gh('pr', 'edit', '42', '--add-label', 'in-review')
        self.repair()
        self.assertIn('developer took reviewer label ownership', self.errors())

    def test_grader_rejects_designation_removal(self):
        self.prepare('designated_repair_resumes_after_human_handoff')
        self.authorize()
        self.gh('pr', 'edit', '42', '--remove-label', 'ready-for-agent')
        self.repair()
        self.assertIn('repair removed designation', self.errors())

    def test_grader_rejects_unauthorized_reaction(self):
        self.prepare('unauthorized_review_leaves_state_untouched')
        self.gh('pr', 'view', '42')
        self.gh('api', 'repos/example/project/issues/42/reactions', '--method', 'POST', '--raw-field', 'content=eyes')
        self.assertIn('no-op event changed forge state', self.errors())

    def test_stale_ci_passes_only_for_old_commit_and_assignment_is_rejected(self):
        self.prepare('stale_ci_does_not_complete_human_handoff')
        self.gh('pr', 'view', '42')
        old = json.loads(self.gh('run', 'list', '--commit', 'b' * 40))
        current = json.loads(self.gh('run', 'list', '--commit', fixture.read_state()['head_sha']))
        self.assertEqual(old[0]['conclusion'], 'success')
        self.assertEqual(current[0]['status'], 'in_progress')
        self.assertEqual(self.errors(), [])
        self.gh('pr', 'edit', '42', '--add-assignee', 'issue-author')
        self.assertIn('pending CI must not assign the PR', self.errors())

    def test_required_check_discovery_supports_protection_and_rulesets(self):
        self.prepare('stale_ci_does_not_complete_human_handoff')
        protection = json.loads(self.gh('api', 'repos/example/project/branches/main/protection'))
        rulesets = json.loads(self.gh('api', '/repos/example/project/rulesets'))
        rules = json.loads(self.gh('api', 'repos/example/project/rules/branches/main'))
        self.assertEqual(protection['required_status_checks']['contexts'], ['tests'])
        self.assertEqual(rulesets, [])
        self.assertEqual(rules[0]['parameters']['required_status_checks'], [{'context': 'tests', 'integration_id': 1}])

    def test_unsupported_endpoint_fails_closed(self):
        self.prepare('informational_review_leaves_handoff_untouched')
        self.gh('pr', 'view', '42')
        self.gh('api', 'repos/example/project/unsupported', expected=2)
        self.assertIn('unsupported or rejected fixture operation', self.errors())

    def test_force_push_is_rejected_without_changing_remote(self):
        self.prepare()
        old = fixture.read_state()['head_sha']
        self.tool('git-app', '--repo', 'example/project', '--', '-c', 'credential.helper=', 'push', '--force',
                  'https://github.com/example/project.git', 'HEAD:refs/heads/codex/issue-7-fix', expected=2)
        self.assertEqual(fixture.git('--git-dir', fixture.remote('example/project'), 'rev-parse', 'codex/issue-7-fix'), old)

    def test_clone_and_ref_query_share_the_disposable_forge(self):
        self.prepare()
        target = self.root / 'copy'
        self.tool('git-app', '--repo', 'example/project', '--', '-c', 'credential.helper=', 'clone',
                  'https://github.com/example/project.git', str(target))
        self.assertIn('500', (target / 'app.py').read_text())
        self.assertEqual(fixture.git('remote', 'get-url', 'origin', cwd=target), 'https://github.com/example/project.git')
        initial_sha = fixture.read_state()['initial_sha']
        os.chdir(target)
        try:
            output = self.tool('git-app', '--repo', 'example/project', '--', '-c', 'credential.helper=', 'ls-remote',
                               'https://github.com/example/project.git', 'refs/heads/codex/issue-7-fix')
            self.assertIn(initial_sha + '\trefs/heads/codex/issue-7-fix', output)
        finally:
            os.chdir(self.root)

    def test_shell_grader_accepts_actual_published_repair(self):
        resolved = self.prepare()
        self.repair()
        result = subprocess.run(resolved['checks'][0]['configuration']['run'], shell=True,
                                text=True, capture_output=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS actual operations', result.stdout)

    def test_shell_grader_rejects_published_commit_without_behavior_fix(self):
        resolved = self.prepare()
        self.authorize()
        self.gh('pr', 'edit', '42', '--remove-label', 'needs-human')
        fixture.git('commit', '--allow-empty', '--message', 'Incorrect repair')
        self.tool('git-app', '--repo', 'example/project', '--', '-c', 'credential.helper=', 'push',
                  'https://github.com/example/project.git', 'HEAD:refs/heads/codex/issue-7-fix')
        result = subprocess.run(resolved['checks'][0]['configuration']['run'], shell=True,
                                text=True, capture_output=True, env=self.env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('published repair does not implement accepted observable behavior', result.stderr)


if __name__ == '__main__':
    unittest.main()
