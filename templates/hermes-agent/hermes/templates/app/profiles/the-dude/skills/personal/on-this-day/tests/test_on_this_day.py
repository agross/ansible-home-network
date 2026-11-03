import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'on_this_day.py'
SPEC = importlib.util.spec_from_file_location('on_this_day', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OnThisDayTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.state = Path(self.temporary_directory.name)
        MODULE.write(self.state / 'candidates.json', {
            'date': MODULE.today(),
            'status': 'ready',
            'events': [{'id': 0, 'year': 1900, 'text': 'A botanical garden opens.'}],
        })
        self.selection = {
            'date': MODULE.today(),
            'event_id': 0,
            'vibe': 'POSITIV',
            'relevance': 'WUERDE_KENNEN',
            'visual_description': 'Visitors gather beside flowering trees in a bright botanical garden.',
        }
        self.image = self.state / 'test.png'
        self.image.write_bytes(b'\x89PNG\r\n\x1a\nfixture')

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_stage_reuses_current_event_token(self):
        first = MODULE.stage(self.state, self.selection)
        self.selection['vibe'] = 'NEGATIV'
        second = MODULE.stage(self.state, self.selection)
        self.assertEqual(second['image_token'], first['image_token'])

    def test_stage_rejects_negative_selection(self):
        self.selection['vibe'] = 'NEGATIV'
        with self.assertRaises(ValueError):
            MODULE.stage(self.state, self.selection)

    def test_generate_uses_configured_hermes_image_provider(self):
        prompt = self.state / 'prompt.txt'
        prompt.write_text('A botanical garden opens.', encoding='utf-8')
        output_dir = self.state / 'images'
        expected = {'paths': [str(output_dir / 'image.png')], 'partial': False}
        with patch.object(MODULE.subprocess, 'run') as run:
            run.return_value.stdout = json.dumps(expected)
            self.assertEqual(MODULE.generate(prompt, output_dir), expected)
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ['/opt/hermes/.venv/bin/python', '-c'])
        self.assertIn('get_active_provider', command[2])
        self.assertIn('_ensure_plugins_discovered', command[2])
        self.assertEqual(command[3:], [str(prompt), str(output_dir)])
        self.assertEqual(run.call_args.kwargs['env'], MODULE.profile_env())

    def test_dry_run_does_not_mark_delivery_attempted(self):
        staged = MODULE.stage(self.state, self.selection)
        self.assertEqual(MODULE.publish(self.state, self.image, staged['image_token'], dry_run=True), {'status': 'dry_run'})
        self.assertFalse((self.state / 'sent.json').exists())

    def test_success_uses_hermes_media_delivery(self):
        staged = MODULE.stage(self.state, self.selection)
        with patch.object(MODULE.subprocess, 'run') as send:
            send.return_value.stdout = json.dumps({'success': True, 'delivered': True, 'message_id': 42})
            self.assertEqual(
                MODULE.publish(self.state, self.image, staged['image_token']),
                {'status': 'sent', 'telegram_message_id': '42'},
            )
        send.assert_called_once_with(
            ['/opt/hermes/.venv/bin/hermes', 'send', '--json', '--to', 'telegram:755375788',
             f'Guten Morgen! Was geschah heute vor {int(MODULE.today()[:4]) - 1900} Jahren? Errätst du, was als Nächstes passierte? MEDIA:{self.image.resolve()}'],
            check=True,
            timeout=300,
            capture_output=True,
            text=True,
            env=MODULE.profile_env(),
        )
        self.assertEqual(MODULE.read(self.state / 'sent.json')['status'], 'sent')

    def test_failed_delivery_blocks_retries(self):
        staged = MODULE.stage(self.state, self.selection)
        with patch.object(MODULE, 'telegram', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                MODULE.publish(self.state, self.image, staged['image_token'])
        self.assertEqual(MODULE.publish(self.state, self.image, staged['image_token']), {'status': 'already_attempted'})


if __name__ == '__main__':
    unittest.main()
