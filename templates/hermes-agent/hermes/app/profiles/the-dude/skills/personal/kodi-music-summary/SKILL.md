---
name: kodi-music-summary
description: Send Alex a daily Telegram summary of tracks recorded by the Kodi music tracker.
version: 1.1.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Kodi, music, Telegram, blueprint]
    blueprint:
      schedule: "0 20 * * *"
      deliver: telegram
      prompt: "At 20:00 Europe/Berlin, run kodi-music-summary. If tracks were recorded, send the generated German summary and clear only those records after successful delivery. If no tracks were recorded, return [SILENT]."
      no_agent: false
---

# Kodi Music Summary

The blueprint runs at 20:00 Europe/Berlin when the profile timezone is
Europe/Berlin. It is a suggested automation.

The deployed `kodi-tracker` Compose service runs `scripts/stream.py`
continuously, polling Kodi every three seconds. It appends
`timestamp|title|artist|file` records to the shared profile log. Use these
recorded plays as the summary source.

1. Run `python3 "${HERMES_SKILL_DIR}/scripts/summary.py"`. It freezes unread
   records into a pending batch. Run one summary delivery at a time.
2. If it prints `No songs played today!`, return `[SILENT]`. A missing log is a
   tracker error: report it rather than treating it as no plays.
3. Send the generated German summary unchanged to Alex through Telegram. After
   confirmed delivery, run
   `python3 "${HERMES_SKILL_DIR}/scripts/summary.py" --clear`, then return
   `[SILENT]` to avoid duplicate cron delivery. If delivery fails or remains
   uncertain, retain the pending batch for retry. If only automatic
   final-response delivery is available, return the summary and retain the
   batch until delivery can be confirmed.

`--clear` acknowledges only the pending batch using a cursor; it preserves the
append-only log and tracks recorded during delivery. Retries render the same
pending batch. The summary covers all unacknowledged plays, including backlog
after a missed run.

Both scripts default to
`${HERMES_HOME:-~/.hermes}/workspace/state/kodi-music-summary/listen.log`.
Compose sets the tracker home to `/opt/data/profiles/the-dude`. For a custom
log, set `KODI_MUSIC_LOG_FILE` to the same shared file for both processes. Keep
the log, `.cursor`, and `.pending` files together; avoid truncating or rotating
the log without migrating its cursor.
