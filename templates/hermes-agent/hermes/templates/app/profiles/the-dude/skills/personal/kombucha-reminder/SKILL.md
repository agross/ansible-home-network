---
name: kombucha-reminder
description: Run the daily Kombucha reminder check, or inspect and adjust its next due date.
metadata:
  hermes:
    tags: [blueprint, telegram, cron]
    blueprint:
      schedule: "0 9 * * *"
      deliver: telegram
      prompt: "Run the kombucha-reminder daily check at 09:00 Europe/Berlin. Send only the reminder when due every six days; otherwise return [SILENT]. Persist the next due date in the state file."
      no_agent: false
---

# Kombucha Reminder

Check daily; send one reminder every six days. The blueprint proposes a scheduled
job for acceptance in Hermes. Before accepting, check for an existing
`kombucha-reminder` job and retain only one daily check.

## Daily check

1. Run the bundled gate once with the persistent state path:

   ```sh
   KOMBUCHA_STATE_FILE="${HERMES_HOME:-$HOME/.hermes}/workspace/state/kombucha-reminder/state.json" python3 "${HERMES_SKILL_DIR}/scripts/kombucha_gate.py"
   ```

2. If stdout is `{"wakeAgent": false}`, return exactly `[SILENT]`.
3. Otherwise, return only the reminder text from stdout. Hermes delivers the
   response to Telegram. A failed script run is an error, not a reminder.

The gate reads `next_due` from the state file. On a due day, it advances that date
by `interval_days` (default: 6) until it is in the future, increments
`cycle_count`, sets `last_fired`, and atomically writes the state before
printing the reminder. Downtime produces one catch-up reminder. A second run on
the same day stays silent.

Missing or unreadable state initializes a reminder due today; the gate saves the
next due date and appends a recovery note to the reminder. A non-due run leaves
state untouched.

## Adjust the reminder

- **Change wording:** edit `TEMPLATE` in `scripts/kombucha_gate.py`.
- **Change interval:** edit `interval_days` in the persistent state file.
- **Move next reminder:** set `next_due` to the desired ISO date (`YYYY-MM-DD`) in that file.
- **Pause or resume:** use `hermes cron pause kombucha-reminder` or
  `hermes cron resume kombucha-reminder`. State retains the next due date.

The accepted blueprint runs this bundled gate directly from
`${HERMES_SKILL_DIR}/scripts/kombucha_gate.py`. It never creates or refreshes a
copied script under `${HERMES_HOME}/scripts`.

## Verify

Use `KOMBUCHA_STATE_FILE` with a temporary file when testing:

- Future `next_due`: sleep-gate JSON, state unchanged.
- Due today: one reminder, saved `next_due` six days later, `cycle_count` incremented.
- Overdue: one reminder, saved `next_due` advanced past today.
- Missing or unreadable state: recovery note and a saved next due date.
- Repeat after a due run: sleep-gate JSON, state unchanged.
