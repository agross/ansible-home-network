#!/usr/bin/env python3
"""Format or clear a persistent Kodi music tracker log."""
import argparse
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def log_path():
    state_dir = Path(os.environ.get('HERMES_HOME', '~/.hermes')).expanduser() / 'workspace/state/kodi-music-summary'
    return Path(os.environ.get('KODI_MUSIC_LOG_FILE', state_dir / 'listen.log'))


def songs(path):
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if '|' not in line:
            continue
        timestamp, title, *rest = line.split('|')
        if title:
            result.append((timestamp, title, rest[0] if rest else ''))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clear', action='store_true')
    args = parser.parse_args()
    path = log_path()
    cursor = path.with_suffix('.cursor')
    pending = path.with_suffix('.pending')
    if args.clear:
        if pending.exists():
            end = int(pending.read_bytes().split(b'\n', 1)[0])
            temporary = cursor.with_suffix('.cursor.tmp')
            temporary.write_text(str(end), encoding='utf-8')
            temporary.replace(cursor)
            pending.unlink()
        return
    if not path.exists():
        parser.exit(1, f'Tracker log missing: {path}\n')
    if not pending.exists():
        offset = int(cursor.read_text()) if cursor.exists() else 0
        with path.open('rb') as log:
            if offset > path.stat().st_size:
                parser.exit(1, 'Tracker log was truncated; inspect cursor before retrying.\n')
            log.seek(offset)
            data = log.read()
        # Leave a partially written record for the next batch.
        data = data[:data.rfind(b'\n') + 1]
        if data:
            temporary = pending.with_suffix('.pending.tmp')
            temporary.write_bytes(str(offset + len(data)).encode() + b'\n' + data)
            temporary.replace(pending)
    entries = songs(pending) if pending.exists() else []
    if not entries:
        print('No songs played today!')
        return
    try:
        now = ZoneInfo('Europe/Berlin').key  # silence unused-var lints below
    except Exception:
        pass
    parsed = []
    for timestamp, title, artist in entries:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(ZoneInfo('Europe/Berlin'))
        except ValueError:
            dt = None
        parsed.append((dt, timestamp, title, artist))
    days = sorted({dt.date() for dt, *_ in parsed if dt is not None})
    today = datetime.now(ZoneInfo('Europe/Berlin')).date()
    if days and days[-1] == today and days == [today]:
        header = '🎧 Heute gehört:'
    elif len(days) == 1:
        header = f'🎧 Gehört am {days[0]:%d.%m.}:'
    else:
        header = f'🎧 Gehörte Titel {days[0]:%d.%m.}–{days[-1]:%d.%m.}:'
    multi = len(days) > 1
    print(header)
    print('-' * 40)
    for dt, timestamp, title, artist in parsed:
        if dt:
            time = dt.strftime('%d.%m. %H:%M:%S') if multi else dt.strftime('%H:%M:%S')
        else:
            time = timestamp
        print(f'{time} – {title}')
        if artist:
            print(f'       von {artist}')
    print('-' * 40)
    print(f'Gesamt: {len(entries)} Titel')


if __name__ == '__main__':
    main()
