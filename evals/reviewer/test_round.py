"""Execute the packaged reviewer helper against the fake forge."""

import fcntl
import hashlib
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

CASES = {item['name']: item for item in json.loads(Path(__file__).with_name('cases.json').read_text())}
HELPER = extension.SKILL / 'scripts/review_round.py'


class ReviewerRoundTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='reviewer-round-test-')
        self.root = Path(self.temporary.name)
        self.previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(os.chdir, self.previous)

    def prepare(self, name='target_tip_advance_keeps_same_comparison'):
        self.case = CASES[name]
        resolved = extension.resolve_case(self.case)
        fixture.git('init')
        fixture.git('config', 'user.name', 'Fixture')
        fixture.git('config', 'user.email', 'fixture@example.invalid')
        for commit in resolved['fixture']['commits']:
            for relative, text in commit['files'].items():
                p = self.root / relative
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            fixture.git('add', '.')
            fixture.git('commit', '--message', commit['message'])
        target = self.root / '.git/fixture-bin'
        target.mkdir()
        for name, text in resolved['fixture']['bin'].items():
            path = target / name
            path.write_text(text)
            path.chmod(0o755)
        fixture.setup(self.case['name'])
        self.env = dict(os.environ, PATH=str(target) + os.pathsep + os.environ['PATH'],
                        HERMES_HOME=str(self.root / '.fixture/profiles/reviewer'))
        return resolved

    def invoke(self, operation, plan=None, expected_exit=0):
        argv = [sys.executable, str(HELPER), operation, '--repo', 'example/project',
                '--number', '42', '--reviewer-app', getattr(self, 'reviewer_app', 'reviewer'),
                '--developer-app', getattr(self, 'developer_app', 'developer')]
        if plan is not None:
            path = self.root / '.git/plan.json'
            path.write_text(json.dumps(plan))
            argv += ['--plan', str(path)]
        completed = subprocess.run(argv, env=self.env, text=True, capture_output=True)
        self.assertEqual(completed.returncode, expected_exit, completed.stderr)
        return json.loads(completed.stdout)

    def plan(self, snapshot):
        return {'basis': snapshot['basis'], 'issue_number': 7, 'state': self.case.get('verdict', 'clean'),
                'body': 'Verified API: nonempty must return 200, not 201; empty must return 400, not 500.',
                'comments': [], 'resolved_threads': [{'id': item, 'evidence': 'app.py and focused regression verified the requested correction'}
                                                    for item in self.case['resolved']]}

    def scan(self):
        result = subprocess.run([str(self.root / '.git/fixture-bin/gh-app'), '--repo', 'example/project', '--',
                                 'api', 'repos/example/project/pulls/42/files'], env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def errors(self):
        operations = [json.loads(line) for line in (fixture.directory() / 'operations.jsonl').read_text().splitlines()]
        return assess(self.case, fixture.load(), operations)

    def completed(self):
        plan = self.plan(self.invoke('inspect'))
        self.assertEqual(self.invoke('begin', plan)['status'], 'begun')
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        self.assertEqual(self.errors(), [])

    def test_misconfigured_app_blocks_before_labels_or_reactions(self):
        self.prepare()
        state = fixture.load()
        state['authenticated_app_slug'] = 'agross-reviewer'
        fixture.save(state)
        plan = {'basis': {'head': state['head'], 'merge_base': state['merge_base'], 'base_ref': 'main'},
                'issue_number': 7}
        result = self.invoke('begin', plan)
        self.assertEqual(result['status'], 'blocked')
        observed = fixture.load()
        self.assertEqual(observed['labels'], ['ready-for-agent', 'role:api'])
        self.assertEqual(observed['issue_labels'], ['ready-for-agent', 'role:api'])
        self.assertEqual(observed['reactions'], state['reactions'])
        self.assertEqual(observed['reviews'], [])

    def test_corrected_app_slugs_review_developer_pr_without_designation(self):
        self.prepare('new_findings_publish_one_pinned_batch')
        self.reviewer_app, self.developer_app = 'agross-reviewer', 'agross-developer'
        state = fixture.load()
        state['authenticated_app_slug'] = self.reviewer_app
        state['developer_app_slug'] = self.developer_app
        state['labels'].remove('ready-for-agent')
        fixture.save(state)
        snapshot = self.invoke('inspect')
        self.assertEqual(snapshot['pr']['user']['login'], 'agross-developer[bot]')
        plan = self.plan(snapshot)
        self.assertEqual(self.invoke('begin', plan)['status'], 'begun')
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        observed = fixture.load()
        self.assertEqual(set(observed['labels']), {'in-review', 'role:api'})
        self.assertEqual(len(observed['reviews']), 1)
        self.assertEqual([item['content'] for item in observed['reactions'] if item['user']['id'] == 20], ['-1'])
        self.assertEqual([item for item in observed['reactions'] if item['user']['id'] == 99],
                         [item for item in state['reactions'] if item['user']['id'] == 99])

    def test_missing_authenticated_app_slug_blocks_identity_inspection(self):
        self.prepare()
        state = fixture.load()
        state['authenticated_app_slug'] = None
        fixture.save(state)
        self.assertEqual(self.invoke('inspect')['status'], 'blocked')
        self.assertEqual(fixture.load()['labels'], state['labels'])
        self.assertEqual(fixture.load()['reactions'], state['reactions'])

    def test_renovate_prs_are_reviewed_without_developer_provenance_or_designation(self):
        self.prepare('renovate_pr_without_designation_is_reviewed')
        snapshot = self.invoke('inspect')
        self.assertEqual(snapshot['pr']['user']['login'], 'renovate[bot]')
        self.assertNotIn('hermes-origin', snapshot['pr']['body'])
        plan = self.plan(snapshot)
        plan.pop('issue_number')
        self.assertEqual(self.invoke('begin', plan)['status'], 'begun')
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        self.assertEqual(self.errors(), [])
        self.assertEqual(set(fixture.load()['labels']), {'role:api', 'needs-human'})

    def test_renovate_findings_publish_without_delegating_to_developer(self):
        self.prepare('renovate_findings_publish_without_developer_delegation')
        plan = self.plan(self.invoke('inspect'))
        plan.pop('issue_number')
        self.assertEqual(self.invoke('begin', plan)['status'], 'begun')
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        self.assertEqual(self.errors(), [])
        self.assertEqual(set(fixture.load()['labels']), {'role:api', 'in-review', 'needs-human'})
        self.assertEqual(fixture.load()['reviews'][0]['state'], 'COMMENTED')

    def test_head_change_stops_before_any_review_publication(self):
        self.prepare('head_change_stops_stale_session')
        plan = self.plan(self.invoke('inspect'))
        self.invoke('begin', plan)
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'stale_head')
        self.assertEqual(self.errors(), [])

    def test_head_change_after_publication_leaves_new_head_handoff_untouched(self):
        self.prepare('head_change_after_publication_stops_handoff')
        plan = self.plan(self.invoke('inspect'))
        self.invoke('begin', plan)
        self.scan()
        result = self.invoke('apply', plan)
        self.assertEqual(result['status'], 'stale_head')
        self.assertNotIn('needs-human', fixture.load()['labels'])
        self.assertEqual(self.errors(), [])

    def test_target_tip_advance_does_not_invalidate_three_dot_review(self):
        self.prepare()
        self.completed()
        state = fixture.load()
        self.assertNotEqual(state['base_tip'], state['merge_base'])
        self.assertEqual(state['scans'], 1)

    def test_merge_base_change_requires_reassessment_before_publication(self):
        self.prepare('merge_base_change_reassesses_once')
        plan = self.plan(self.invoke('inspect'))
        self.invoke('begin', plan)
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'basis_changed')
        self.assertEqual(fixture.load()['reviews'], [])
        plan = self.plan(self.invoke('inspect'))
        self.invoke('begin', plan)
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        self.assertEqual(self.errors(), [])

    def test_churning_comparison_never_publishes_a_stale_assessment(self):
        self.prepare('merge_base_churn_stops_after_two_restarts')
        for attempt in range(3):
            plan = self.plan(self.invoke('inspect'))
            self.invoke('begin', plan)
            self.scan()
            self.assertEqual(self.invoke('apply', plan)['status'], 'basis_changed')
        self.assertEqual(fixture.load()['scans'], 3)
        self.assertEqual(self.errors(), [])

    def test_verified_app_and_human_threads_close_before_clean_review(self):
        self.prepare('verified_app_and_human_threads_are_resolved')
        self.completed()
        state = fixture.load()
        self.assertTrue(all(thread['isResolved'] for thread in state['threads']))

    def test_unverified_human_thread_blocks_clean_and_stays_open(self):
        self.prepare('unfixed_human_thread_stays_actionable')
        plan = self.plan(self.invoke('inspect'))
        self.invoke('begin', plan)
        self.scan()
        plan['state'] = 'clean'
        self.assertEqual(self.invoke('apply', plan)['status'], 'blocked')
        self.assertFalse(fixture.load()['threads'][0]['isResolved'])
        self.assertEqual(fixture.load()['reviews'], [])
        plan['state'] = 'changes-requested'
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        self.assertEqual(self.errors(), [])

    def test_missing_thread_correction_evidence_cannot_resolve_a_thread(self):
        self.prepare('verified_app_and_human_threads_are_resolved')
        plan = self.plan(self.invoke('inspect'))
        plan['resolved_threads'][0]['evidence'] = ''
        self.assertEqual(self.invoke('apply', plan)['status'], 'blocked')
        self.assertFalse(any(thread['isResolved'] for thread in fixture.load()['threads']))

    def test_inspection_includes_later_thread_comment_pages(self):
        self.prepare('verified_app_and_human_threads_are_resolved')
        state = fixture.load()
        state['threads'][0]['comments']['pageInfo'] = {'hasNextPage': True, 'endCursor': 'COMMENTS_1'}
        state['comment_pages'] = {'APP_THREAD': {'nodes': [{'id': 'LATER', 'body': 'Additional correction to verify',
            'path': 'app.py', 'author': {'login': 'human'}}], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}}
        fixture.save(state)
        result = self.invoke('inspect')
        self.assertEqual(result['threads'][0]['comments']['nodes'][-1]['id'], 'LATER')
        self.assertFalse(result['threads'][0]['comments']['pageInfo']['hasNextPage'])

    def test_existing_marker_resumes_missing_labels_without_duplicate_review(self):
        self.prepare('existing_marker_recovers_missing_finalization')
        plan = self.plan(self.invoke('inspect'))
        self.assertEqual(self.invoke('begin', plan)['status'], 'resume')
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        self.assertEqual(fixture.load()['publication_attempts'], 0)
        self.assertEqual(self.errors(), [])

    def test_completed_marker_is_an_idempotent_noop(self):
        self.prepare('completed_marker_is_idempotent')
        plan = self.plan(self.invoke('inspect'))
        self.assertEqual(self.invoke('begin', plan)['status'], 'resume')
        self.assertEqual(self.invoke('apply', plan)['status'], 'already_complete')
        self.assertEqual(self.errors(), [])

    def test_concurrent_owner_result_suppresses_new_findings_publication(self):
        self.prepare('concurrent_result_prevents_duplicate_comments')
        plan = self.plan(self.invoke('inspect'))
        self.invoke('begin', plan)
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'already_complete')
        self.assertEqual(self.errors(), [])

    def test_new_findings_are_one_pinned_comment_batch(self):
        self.prepare('new_findings_publish_one_pinned_batch')
        self.completed()
        state = fixture.load()
        self.assertEqual(state['publication_attempts'], 1)
        self.assertEqual(state['reviews'][0]['commit_id'], state['initial_head'])

    def test_accepted_ambiguous_publication_is_read_back_without_retry(self):
        self.prepare('accepted_but_ambiguous_publication_is_reconciled')
        self.completed()
        self.assertEqual(fixture.load()['publication_attempts'], 1)

    def test_unconfirmed_publication_stops_without_blind_retry(self):
        self.prepare()
        state = fixture.load(); state['reject_publication'] = True; fixture.save(state)
        plan = self.plan(self.invoke('inspect'))
        self.invoke('begin', plan)
        self.assertEqual(self.invoke('apply', plan)['status'], 'blocked')
        self.assertEqual(fixture.load()['publication_attempts'], 1)
        self.assertEqual(fixture.load()['reviews'], [])

    def test_later_invocation_recovers_failed_labels_without_reposting(self):
        self.prepare('published_marker_recovers_after_label_failure')
        plan = self.plan(self.invoke('inspect'))
        self.invoke('begin', plan)
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'blocked')
        self.assertEqual(fixture.load()['publication_attempts'], 1)
        plan = self.plan(self.invoke('inspect'))
        self.assertEqual(self.invoke('begin', plan)['status'], 'resume')
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        self.assertEqual(self.errors(), [])

    def test_publication_lock_blocks_an_overlapping_local_writer(self):
        self.prepare()
        plan = self.plan(self.invoke('inspect'))
        root = Path(self.env['HERMES_HOME']) / 'review-locks'
        root.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(b'example/project#42').hexdigest()
        with (root / key).open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.invoke('apply', plan)['status'], 'busy')
        self.assertEqual(fixture.load()['reviews'], [])

    def test_legacy_marker_without_comparison_evidence_blocks_duplicate_review(self):
        self.prepare('existing_marker_recovers_missing_finalization')
        state = fixture.load()
        state['reviews'][0]['body'] = state['reviews'][0]['body'].splitlines()[0]
        fixture.save(state)
        self.assertEqual(self.invoke('inspect')['status'], 'blocked')
        self.assertEqual(fixture.load()['publication_attempts'], 0)

    def test_another_users_marker_does_not_suppress_the_reviewers_result(self):
        self.prepare('existing_marker_recovers_missing_finalization')
        state = fixture.load()
        state['reviews'][0]['user'] = {'id': 99, 'login': 'human', 'type': 'User'}
        fixture.save(state)
        snapshot = self.invoke('inspect')
        self.assertIsNone(snapshot['existing'])
        plan = self.plan(snapshot)
        self.assertEqual(self.invoke('begin', plan)['status'], 'begun')
        self.scan()
        self.assertEqual(self.invoke('apply', plan)['status'], 'complete')
        state = fixture.load()
        self.assertEqual(state['publication_attempts'], 1)
        self.assertEqual(state['reviews'][-1]['user']['id'], 20)

    def test_label_list_readbacks_return_actual_labels_without_mutation(self):
        self.prepare()
        before = fixture.load()
        tool = self.root / '.git/fixture-bin/gh-app'
        for number, key in ((42, 'labels'), (7, 'issue_labels')):
            with self.subTest(number=number):
                result = subprocess.run([str(tool), '--repo', 'example/project', '--', 'api',
                    f'repos/example/project/issues/{number}/labels'], env=self.env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual({item['name'] for item in json.loads(result.stdout)}, set(before[key]))
        self.assertEqual(fixture.load()['labels'], before['labels'])
        self.assertEqual(fixture.load()['issue_labels'], before['issue_labels'])

    def test_all_cases_keep_expected_assertions_outside_fixture(self):
        self.assertEqual(len(CASES), 16)
        for case in CASES.values():
            with self.subTest(case=case['name']):
                resolved = extension.resolve_case(case)
                self.assertEqual(resolved['id'], case['name'])
                self.assertLessEqual(len(resolved['checks'][0]['configuration']['run']), 4096)
                event = json.loads(resolved['fixture']['commits'][0]['files']['event.json'])
                self.assertNotIn('outcomes', event)
                self.assertNotIn('resolved', event)
                self.assertEqual(resolved['checks'][2]['configuration']['kind'], 'unchanged')


if __name__ == '__main__':
    unittest.main()
