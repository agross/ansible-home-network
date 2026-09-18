#!/usr/bin/env python3
"""Persistent state and Telegram delivery for the daily historical image game."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

PREFERENCES = json.loads((Path(__file__).resolve().parents[1] / 'references/preferences.json').read_text())
BERLIN = ZoneInfo('Europe/Berlin')


def profile_home():
    return Path(os.environ.get('HERMES_HOME', '/opt/data/profiles/the-dude'))


def profile_env():
    environment = dict(os.environ)
    dotenv = profile_home() / '.env'
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                environment.setdefault(key, value)
    return environment


def today():
    return datetime.now(BERLIN).date().isoformat()


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def write(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def blocked(text):
    return any(word.casefold() in text.casefold() for word in PREFERENCES['BLOCKED_KEYWORDS'])


def request(url, payload=None, headers=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def prepared(state):
    date = today()
    sent = read(state / 'sent.json')
    if sent and sent.get('date') == date:
        return {'status': 'already_attempted'}
    path = state / 'candidates.json'
    cached = read(path)
    if cached and cached.get('date') == date:
        return cached
    feed = request('https://de.wikipedia.org/api/rest_v1/feed/onthisday/events/' + date[5:].replace('-', '/'),
                   headers={'User-Agent': 'OnThisDayHermes/1.0'})
    events = []
    for event in feed.get('events', []):
        year, text = event.get('year'), event.get('text')
        if isinstance(year, int) and isinstance(text, str) and text and year < int(date[:4]) and not blocked(text):
            events.append({'id': len(events), 'year': year, 'text': text})
    result = {'date': date, 'status': 'ready' if events else 'no_candidates', 'events': events}
    write(path, result)
    return result


def select(state, selection):
    candidates = read(state / 'candidates.json')
    if not isinstance(selection, dict) or not candidates or candidates.get('date') != today() or selection.get('date') != today():
        raise ValueError('Selection must match the current Berlin date.')
    if selection.get('vibe') not in ('POSITIV', 'NEUTRAL') or selection.get('relevance') not in ('WUERDE_KENNEN', 'NICHT_KENNEN'):
        raise ValueError('Event must be positive or neutral with a valid relevance label.')
    event_id = selection.get('event_id')
    event = next((candidate for candidate in candidates['events'] if type(event_id) is int and candidate['id'] == event_id), None)
    if event is None or blocked(event['text']):
        raise ValueError('Selection contains an invalid or blocked event.')
    description = selection.get('visual_description')
    if not isinstance(description, str) or not description.strip() or len(description.split()) > 100:
        raise ValueError('Visual description must contain 1–100 words.')
    return dict(event, date=today(), years_ago=int(today()[:4]) - event['year'], image_prompt=description,
                vibe=selection['vibe'], relevance=selection['relevance'])


def image_request(event):
    return {'status': 'image_required', 'image_token': event['image_token'],
            'prompt': 'MODERN DIGITAL ILLUSTRATION: ' + event['image_prompt'] +
            ', WHOLE BODY/FULL FIGURE focus on human figures when present, warm bright lighting, '
            'contemporary art aesthetic, NO text/logos/dates'}


def stage(state, selection):
    sent = read(state / 'sent.json')
    if sent and sent.get('date') == today():
        return {'status': 'already_attempted'}
    event = read(state / 'event.json')
    if event and event.get('date') == today():
        return image_request(event)
    event = select(state, selection)
    event['image_token'] = uuid.uuid4().hex
    write(state / 'event.json', event)
    return image_request(event)


def telegram(path, caption, chat):
    """Send media and require Telegram's concrete message receipt.

    The cron agent's final response is auto-delivered to the same Telegram chat.
    This helper performs the real media delivery, so it removes the cron
    duplicate-delivery context before invoking ``hermes send``. Otherwise the
    CLI returns a successful-but-skipped response without a message ID.
    """
    send_env = profile_env()
    for key in tuple(send_env):
        if key.startswith('HERMES_CRON_AUTO_DELIVER_'):
            send_env.pop(key, None)
    result = subprocess.run(
        ['/opt/hermes/.venv/bin/hermes', 'send', '--json', '--to', f'telegram:{chat}',
         f'{caption} MEDIA:{path.resolve()}'],
        check=True,
        timeout=300,
        capture_output=True,
        text=True,
        env=send_env,
    )
    try:
        receipt = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError('Telegram send returned no machine-readable receipt.') from exc
    message_id = receipt.get('message_id')
    if not receipt.get('success') or receipt.get('delivered') is False or message_id is None:
        raise RuntimeError('Telegram send was not positively acknowledged with a message ID.')
    return {'telegram_message_id': str(message_id)}


def generate(prompt_file, output_dir):
    runner = '''
import json
import shutil
import sys
import urllib.request
import uuid
from pathlib import Path

from agent.image_gen_registry import get_active_provider
from hermes_cli.plugins import _ensure_plugins_discovered

prompt = Path(sys.argv[1]).read_text(encoding='utf-8')
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)
_ensure_plugins_discovered()
provider = get_active_provider()
if provider is None:
    raise RuntimeError('No configured Hermes image generation provider.')
payload = provider.generate(prompt, aspect_ratio='landscape')
if not payload.get('success'):
    raise RuntimeError(payload.get('error', 'Hermes image generation failed.'))
source = payload.get('image')
if not isinstance(source, str) or not source:
    raise RuntimeError('Hermes image generation returned no image.')
destination = output_dir / f'on-this-day-{uuid.uuid4().hex}.png'
if source.startswith(('https://', 'http://')):
    urllib.request.urlretrieve(source, destination)
else:
    shutil.copyfile(source, destination)
print(json.dumps({'paths': [str(destination)], 'partial': False}))
'''
    result = subprocess.run(
        ['/opt/hermes/.venv/bin/python', '-c', runner, str(prompt_file), str(output_dir)],
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
        env=profile_env(),
    )
    return json.loads(result.stdout)


def publish(state, image_path, image_token, dry_run=False):
    sent = read(state / 'sent.json')
    if sent and sent.get('date') == today():
        return {'status': 'already_attempted'}
    event = read(state / 'event.json')
    if not event or event.get('date') != today() or event.get('image_token') != image_token:
        raise ValueError('Image must match the current staged event token and Berlin date.')
    path = Path(image_path)
    content = path.read_bytes()
    if not (content.startswith(b'\x89PNG\r\n\x1a\n') or content.startswith(b'\xff\xd8\xff')):
        raise ValueError('Expected a local PNG or JPEG from minimax-image-gen.')
    if dry_run:
        return {'status': 'dry_run'}
    delivery = {'date': event['date'], 'status': 'attempted'}
    write(state / 'sent.json', delivery)
    caption = f"Guten Morgen! Was geschah heute vor {event['years_ago']} Jahren? Errätst du, was als Nächstes passierte?"
    receipt = telegram(path, caption, os.environ.get('ONTHISDAY_CHAT_ID', '755375788'))
    delivery.update(receipt)
    delivery['status'] = 'sent'
    write(state / 'sent.json', delivery)
    return {'status': 'sent', **receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'stage', 'generate', 'publish', 'answer'])
    parser.add_argument('--state-dir', type=Path, default=Path(os.environ.get('HERMES_HOME', '~/.hermes')).expanduser() / 'workspace/state/on-this-day')
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--image-token')
    parser.add_argument('--prompt-file', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (args.state_dir / 'run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'locked'}))
            return
        if args.command == 'prepare':
            result = prepared(args.state_dir)
        elif args.command == 'stage':
            if args.selection is None:
                parser.error('stage requires --selection')
            result = stage(args.state_dir, read(args.selection))
        elif args.command == 'answer':
            result = read(args.state_dir / 'event.json') or {'status': 'no_saved_event'}
        elif args.command == 'generate':
            if args.prompt_file is None or args.output_dir is None:
                parser.error('generate requires --prompt-file and --output-dir')
            result = generate(args.prompt_file, args.output_dir)
        else:
            if args.image is None or not args.image_token:
                parser.error('publish requires --image and --image-token')
            result = publish(args.state_dir, args.image, args.image_token, args.dry_run)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'error', 'type': type(exc).__name__,
                          'message': str(exc) if isinstance(exc, ValueError) else 'Operation failed; inspect state before retrying.'}), file=sys.stderr)
        sys.exit(1)
