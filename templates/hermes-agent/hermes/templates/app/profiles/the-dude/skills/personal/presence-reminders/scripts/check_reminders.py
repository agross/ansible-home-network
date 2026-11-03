#!/usr/bin/env python3
"""Deterministic presence-reminder check.

Reads reminders.json, queries both ioBroker instances' REST API directly
(basic auth, /v1/state/<id>), prints due reminder lines, and atomically
rewrites the state file keeping only not-due entries. No LLM decisions.
"""
import base64
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

HERMES_HOME = Path(os.environ.get('HERMES_HOME', '/opt/data/profiles/the-dude'))
STATE = HERMES_HOME / 'workspace/state/presence-reminders/reminders.json'
STATE_ID = 'ping.0.iobroker.mobile-phone-{person}'
HOSTS = {'home': 'https://iobroker.home.therightstuff.de',
         'garden': 'https://iobroker.ogd.therightstuff.de'}
USERS = {'home': 'claw', 'garden': 'claw'}
PASSWORD_ENV = {'home': 'IOBROKER_HOME_PASSWORD', 'garden': 'IOBROKER_OGD_PASSWORD'}
PERSONS = ('alex', 'sonja')
SITES = ('home', 'garden')
GERMAN = {
    ('alex', 'home'): '🏠 Alex ist zuhause! Erinnerung:',
    ('alex', 'garden'): '🌳 Alex ist im Garten! Erinnerung:',
    ('sonja', 'home'): '🏡 Sonja ist zuhause! Erinnerung:',
    ('sonja', 'garden'): '🌿 Sonja ist im Garten! Erinnerung:',
}


def load_env():
    dot = HERMES_HOME / '.env'
    if dot.exists():
        for line in dot.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                os.environ.setdefault(k, v)


def read_presence(site, person):
    """Return True/False, or None when the read is uncertain."""
    pwd = os.environ.get(PASSWORD_ENV[site], '')
    if not pwd:
        return None
    auth = 'Basic ' + base64.b64encode(f'{USERS[site]}:{pwd}'.encode()).decode()
    path = '/v1/state/' + STATE_ID.format(person=person)
    try:
        req = urllib.request.Request(HOSTS[site] + path, headers={'Authorization': auth})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return bool(data.get('val'))
    except Exception:
        return None  # uncertain


def main():
    load_env()
    STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        reminders = json.loads(STATE.read_text())
    except Exception:
        reminders = {}

    due = []
    kept = {p: {s: list((reminders.get(p) or {}).get(s) or []) for s in SITES} for p in PERSONS}
    for person in PERSONS:
        for site in SITES:
            items = kept[person][site]
            if not items:
                continue
            val = read_presence(site, person)
            if val is True:
                label = GERMAN[(person, site)]
                due.extend(f'{label} {item}' for item in items)
                kept[person][site] = []      # delivered in this same turn
            # val False → not due, keep; val None → uncertain, keep (repeat-risk
            # preferred over a lost reminder)

    if due:
        fd = tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=str(STATE.parent))
        with fd:
            json.dump(kept, fd, ensure_ascii=False, indent=2)
            name = fd.name
        os.replace(name, STATE)

    out = '\n'.join(due)
    if out:
        print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
