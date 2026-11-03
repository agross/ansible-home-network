#!/usr/bin/env python3
"""Poll Kodi and append played tracks to the summary log."""
import base64
import json
import os
import time
from datetime import datetime
from urllib.request import Request, urlopen

from summary import log_path


def rpc(method, params=None):
    host = os.environ['KODI_HOST']
    port = os.environ.get('KODI_PORT', '8081')
    credentials = f"{os.environ['KODI_USER']}:{os.environ['KODI_PASS']}"
    auth = base64.b64encode(credentials.encode()).decode()
    request = Request(
        f'http://{host}:{port}/jsonrpc',
        data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                         'params': params or {}}).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Basic {auth}'},
    )
    with urlopen(request, timeout=5) as response:
        payload = json.load(response)
    return payload['result']


def current_track():
    for player in rpc('Player.GetActivePlayers'):
        if player.get('type') != 'audio':
            continue
        item = rpc('Player.GetItem', {
            'playerid': player['playerid'], 'properties': ['title', 'artist', 'file'],
        })['item']
        if item.get('type') == 'song':
            artist = item.get('artist') or ['']
            fields = (item.get('title') or item.get('label') or 'Unknown',
                      artist[0], item.get('file', ''))
            return '|'.join(str(field).replace('|', ' / ').replace('\n', ' ').replace('\r', ' ')
                            for field in fields)
    return None


def main():
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    # Preserve restart deduplication from the OpenClaw tracker.
    with path.open(encoding='utf-8') as log:
        last = None
        for line in log:
            last = line.rstrip('\n').partition('|')[2] or None
    while True:
        try:
            track = current_track()
            if track is not None and track != last:
                with path.open('a', encoding='utf-8') as log:
                    log.write(f'{datetime.now().astimezone().isoformat()}|{track}\n')
                print('Logged Kodi track', flush=True)
            last = track
        except Exception as error:
            # Preserve the last track during temporary connection failures.
            print(f'Kodi poll failed: {type(error).__name__}', flush=True)
        time.sleep(3)


if __name__ == '__main__':
    main()
