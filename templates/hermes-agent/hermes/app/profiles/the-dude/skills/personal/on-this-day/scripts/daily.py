#!/usr/bin/env python3
"""Deterministic end-to-end runner for the On-This-Day daily game.

One command for the cron job: prepare -> select -> stage -> generate -> publish.
No LLM agent in the loop for procedural steps; the only inference call is a
single `hermes chat` request that classifies the events and writes the visual
description. State lives under ${HERMES_HOME}/workspace/state/on-this-day.
Never runs paid steps when today's delivery marker is already 'sent'.

Usage: python3 daily.py        # runs the full pipeline for today (Berlin date)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

HERMES = '/opt/hermes/.venv/bin/hermes'
SKILL_DIR = Path(__file__).resolve().parents[1]


def today():
    """Today's date from the environment timezone (cron sets TZ=Europe/Berlin)."""
    return date.today().isoformat()


def state_dir():
    home = os.environ.get('HERMES_HOME', '/opt/data/profiles/the-dude')
    return Path(home) / 'workspace/state/on-this-day'


def read(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def write_json(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = tempfile.NamedTemporaryFile('w', delete=False, dir=str(p.parent), encoding='utf-8')
    with fd:
        json.dump(v, fd, ensure_ascii=False, indent=2)
        name = fd.name
    os.replace(name, p)


def env():
    e = dict(os.environ)
    e.setdefault('HERMES_HOME', '/opt/data/profiles/the-dude')
    dotenv = Path(e['HERMES_HOME']) / '.env'
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                e.setdefault(k, v)
    e['PATH'] = '/opt/hermes/.venv/bin:' + e.get('PATH', '')
    return e


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def run_py(args, timeout=600):
    r = subprocess.run([sys.executable] + args, env=env(), capture_output=True, text=True, timeout=timeout)
    if r.stdout:
        log('child stdout: %s' % r.stdout[:400])
    if r.stderr:
        log('child stderr: %s' % r.stderr[:400])
    return r


def llm(prompt):
    """One small inference call for selection + visual description."""
    r = subprocess.run([HERMES, 'chat', '--provider', 'opencode-go', '-m', 'glm-5.3-flash', '-q', prompt],
                       env=env(), capture_output=True, text=True, timeout=240)
    return r.stdout.strip() if r.returncode == 0 else ''


def pick_event(events):
    """Pick an event deterministically with one LLM assist; returns (event, description) or (None, None)."""
    prefs = json.loads((SKILL_DIR / 'references/preferences.json').read_text())
    blocked = [w.casefold() for w in prefs['BLOCKED_KEYWORDS']]

    def bm(t):
        t = t.casefold()
        return any(w in t for w in blocked)

    cand = [e for e in events if not bm(e['text'])]
    if not cand:
        return None, None
    listing = '\n'.join(f"{e['id']} ({e['year']}): {e['text']}" for e in cand[:25])
    prompt = (
        "You help pick one historical daily-guess event from a German list. "
        "Return ONLY compact JSON: {\"event_id\": <int>, \"visual_description\": \"<english 60-90 words>\"}. "
        "Choose the first POSITIV-relevant event you are fairly sure Alex (a German tech-savvy adult) would know; "
        "skip war/terror/violence-like events entirely. The visual_description must show the moment seconds BEFORE the "
        "event happened: visible setting, people, actions, objects — no text, logos, dates, or labels in the scene.\n\n"
        + listing)
    out = llm(prompt)
    m = re.search(r'\{.*\}', out, re.S)
    desc, eid = None, None
    if m:
        try:
            d = json.loads(m.group(0))
            eid, desc = d.get('event_id'), (d.get('visual_description') or '').strip()
        except Exception:
            pass
    ev = next((e for e in cand if eid is not None and e['id'] == eid), None)
    if ev is None:
        ev = cand[0]  # deterministic fallback: first non-blocked entry
    if not desc or not (10 <= len(desc.split()) <= 110):
        desc = ('A quiet everyday scene related to: ' + ev['text'][:120] +
                '. Show the seconds before it happened through setting, people and objects only.')
    return ev, desc


def main():
    state = state_dir()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    now = today()
    sent = read(state / 'sent.json')
    if sent and sent.get('date') == now and sent.get('status') == 'sent':
        log('already delivered today; not spending again.')
        print(json.dumps({'status': 'already_sent'}))
        return 0

    prep = run_py([str(SKILL_DIR / 'scripts/on_this_day.py'), 'prepare'])
    try:
        data = json.loads(prep.stdout)
    except Exception:
        log('prepare failed')
        print(json.dumps({'status': 'error', 'stage': 'prepare'}))
        return 1
    if data.get('status') != 'ready':
        log('prepare: %s' % data.get('status'))
        print(json.dumps({'status': 'no_event'}))
        return 0

    ev, desc = pick_event(data['events'])
    if ev is None:
        log('no candidate')
        print(json.dumps({'status': 'no_event'}))
        return 0
    sel = {'date': now, 'event_id': ev['id'], 'vibe': 'POSITIV', 'relevance': 'WUERDE_KENNEN',
           'visual_description': desc}
    selp = state / f'selection-{now}.json'
    write_json(selp, sel)

    stg = run_py([str(SKILL_DIR / 'scripts/on_this_day.py'), 'stage', '--selection', str(selp)])
    try:
        sd = json.loads(stg.stdout)
    except Exception:
        print(json.dumps({'status': 'error', 'stage': 'stage'}))
        return 1
    if sd.get('status') != 'image_required':
        print(json.dumps({'status': 'error', 'stage': 'stage'}))
        return 1
    pf = state / f'prompt-{now}.txt'
    pf.write_text(sd['prompt'], encoding='utf-8')

    outdir = state / 'images'
    gen = run_py([str(SKILL_DIR / 'scripts/on_this_day.py'), 'generate',
                  '--prompt-file', str(pf), '--output-dir', str(outdir)], timeout=380)
    try:
        gd = json.loads(gen.stdout)
    except Exception:
        print(json.dumps({'status': 'error', 'stage': 'generate'}))
        return 1
    paths = gd.get('paths') or []
    if len(paths) < 1 or gd.get('partial'):
        print(json.dumps({'status': 'error', 'stage': 'generate'}))
        return 1
    img = paths[0]

    pub = run_py([str(SKILL_DIR / 'scripts/on_this_day.py'), 'publish',
                  '--image', img, '--image-token', sd['image_token']], timeout=380)
    try:
        pd = json.loads(pub.stdout)
    except Exception:
        print(json.dumps({'status': 'error', 'stage': 'publish'}))
        return 1
    return 0 if pd.get('status') == 'sent' else 1


if __name__ == '__main__':
    sys.exit(main())
