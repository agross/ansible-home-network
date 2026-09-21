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
    r = subprocess.run([HERMES, 'chat', '-Q', '--provider', 'opencode-go', '-m', 'glm-5.3-flash', '-q', prompt],
                       env=env(), capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        log(f'llm failed rc={r.returncode}: {r.stdout.strip()[:200]}')
    return r.stdout.strip(), r.returncode


def extract_json_string(text, key):
    """Return the value for *key* from the last valid JSON object/line in *text*.

    CLI banners wrap the answer box around the JSON, and the model may emit
    literal newlines inside string values. Try tolerant parses over progressively
    smaller candidate objects instead of a single greedy regex shot.
    """
    candidates = []
    trimmed = text.strip()
    for start in range(len(trimmed)):
        if trimmed[start] == '{':
            candidates.append(trimmed[start:])
    # Prefer compact single-line candidates: find the LAST balanced {...}
    # (grep-like) as well as the greedy one.
    for m in list(re.finditer(r'\{[^{}]*\}', trimmed)):
        candidates.append(m.group(0))
    for cand in candidates:
        try:
            return json.loads(cand).get(key)
        except Exception:
            continue
    return None


def pick_event(events):
    """Pick an event deterministically with one LLM assist; returns (event, description) or (None, None)."""
    prefs = json.loads((SKILL_DIR / 'references/preferences.json').read_text())
    blocked = [w.casefold() for w in prefs['BLOCKED_KEYWORDS']]

    def bm(t):
        t = t.casefold()
        return any(w in t for w in blocked)

    # The feed's keyword blocklist handles broad themes.  These additional
    # terms reject negative current-affairs/disaster items that would otherwise
    # make a poor guessing game even when an LLM happens to return valid JSON.
    negative_markers = (
        'skandal', 'betrug', 'korruption', 'unglück', 'katastrophe', 'brand',
        'todes', 'getötet', 'ermordet', 'absturz', 'hurrikan', 'flut',
    )
    cand = [e for e in events if not bm(e['text'])
            and not any(marker in e['text'].casefold() for marker in negative_markers)]
    if not cand:
        return None, None
    # Evaluate candidates in feed order and stop at the first acceptable one.
    # Events must not be ranked against each other; the first candidate that
    # passes is chosen, so later candidates are never evaluated once a match
    # exists. If a candidate has no concrete, positive visual scene, move to
    # the next feed item instead of giving up after an arbitrary retry limit.
    # This spends text-selection calls only; MiniMax is called exactly once,
    # after a candidate passes validation.
    generic_markers = ('quiet everyday scene related to', 'show the seconds before it happened through')
    for candidate in cand:
        prompt = (
            "You evaluate ONE historical event for Alex's daily image guessing game. "
            "Return ONLY compact JSON: {\"visual_description\": \"<english 60-90 words>\"} "
            "when the event is positive or neutral, relevant to a German tech-savvy adult, "
            "and can be shown through specific people, actions, setting and objects seconds before it happened. "
            "Return ONLY null if it is negative, unsuitable, or cannot yield concrete visual clues. "
            "Never include text, logos, dates or labels in the scene.\n\n"
            f"Event: {candidate['year']}: {candidate['text']}"
        )
        out, rc = llm(prompt)
        if rc != 0:
            # Infrastructure failure (no credentials, network, CLI error): this
            # is NOT an unsuitable candidate. Abort loudly instead of burning
            # every remaining candidate and silently reporting no_event.
            log('llm subcall failed; aborting run as error.')
            import builtins
            builtins.OTD_ABORT = 'PROVIDER_UNREACHABLE'
            return None, None
        desc = extract_json_string(out, 'visual_description')
        if desc is None:
            continue
        desc = desc.strip()
        if not (20 <= len(desc.split()) <= 110):
            continue
        if any(marker in desc.casefold() for marker in generic_markers):
            continue
        return candidate, desc
    return None, None


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

    import builtins
    builtins.OTD_ABORT = None
    ev, desc = pick_event(data['events'])
    if builtins.OTD_ABORT:
        return 1
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

    # Delivery path: the scheduler auto-delivers this job's FINAL RESPONSE to the
    # configured Telegram home channel (same proven mechanism as the other daily
    # jobs). No direct hermes send from inside the cron agent — it trips the
    # cron duplicate-delivery skip. Record the marker locally and return the
    # caption plus image as the final response.
    delivery = {'date': now, 'status': 'sent'}
    write_json(state / 'sent.json', delivery)
    caption = (f"Guten Morgen! Was geschah heute vor {int(now[:4]) - ev['year']} Jahren? "
               "Errätst du, was als Nächstes passierte?")
    print(f"{caption}\nMEDIA:{img}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
