#!/usr/bin/env python3
"""Kombucha reminder gate — daily tick, fires only every 6th day (Berlin calendar).

Runs as a no_agent cron job: stdout is delivered verbatim; ``{"wakeAgent": false}``
or empty output = completely silent. Output contract is also agent-mode compatible:
a due-day's reminder text as the last stdout line would wake a gated agent with it.

State: scripts/state/kombucha-reminder.json (override with KOMBUCHA_STATE_FILE for tests).
Deleting/corrupting the state re-initializes with next_due = today (safe direction:
an extra reminder beats a silently dead one) and flags it in the message.
"""
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

INTERVAL_DAYS = 6
TZ = ZoneInfo("Europe/Berlin")
# Edit the reminder wording here — this is the single source of the message text.
TEMPLATE = (
    "\U0001f9cb Kombucha time! Bottle the current batch and start the next one. "
    "(cycle #{cycle} \u00b7 next reminder: {next_due})"
)
DEFAULT_STATE = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser() / "workspace/state/kombucha-reminder/state.json"


def today() -> date:
    return datetime.now(TZ).date()


def load_state(path: Path) -> dict:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        date.fromisoformat(str(state["next_due"]))  # validates the key really is a date
        return state
    except Exception:
        return {
            "interval_days": INTERVAL_DAYS,
            "next_due": today().isoformat(),
            "cycle_count": 0,
            "last_fired": None,
            "note": "state was missing or unreadable - re-initialized",
        }


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".kombucha_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)  # atomic — no torn state on crash
    except BaseException:
        with open(tmp, "rb"):
            pass
        os.unlink(tmp)
        raise


def main() -> int:
    state_path = Path(os.environ.get("KOMBUCHA_STATE_FILE") or DEFAULT_STATE)
    now = today()
    state = load_state(state_path)

    interval = int(state.get("interval_days") or INTERVAL_DAYS)
    if interval < 1:
        interval = INTERVAL_DAYS
    try:
        due = date.fromisoformat(str(state["next_due"]))
    except ValueError:
        due = now

    if now < due:
        # Not due today: silent in no_agent mode, sleep-gate in agent mode.
        print(json.dumps({"wakeAgent": False}))
        return 0

    # Due (or overdue): one reminder, then catch next_due up past today.
    note = state.pop("note", None)
    while due <= now:
        due += timedelta(days=interval)
    state["interval_days"] = interval
    state["next_due"] = due.isoformat()
    state["cycle_count"] = int(state.get("cycle_count") or 0) + 1
    state["last_fired"] = now.isoformat()
    save_state(state_path, state)

    message = TEMPLATE.format(cycle=state["cycle_count"], next_due=state["next_due"])
    if note:
        message += f" [{note}]"
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
