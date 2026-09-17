# Configuration

The skill blueprint proposes a daily 06:30 schedule. Set the Hermes profile timezone to `Europe/Berlin` so `30 6 * * *` runs at 06:30 Berlin time, including daylight-saving changes. Hermes presents the blueprint as a suggestion; accept it only when the Telegram destination is configured as intended.

This skill uses Hermes’ configured Telegram integration through `hermes send`; it has no Telegram credential of its own.

State is stored in `${HERMES_HOME:-~/.hermes}/on-this-day`. Retain it across restarts and backups. A `sent.json` entry for today blocks all later automatic delivery attempts, including after a timeout.

## Offline verification

Use an isolated state directory. Create `candidates.json` with today's Berlin date and a harmless candidate, then create a selection JSON with matching `date`, `event_id`, `vibe`, `relevance`, and a 1–100 word `visual_description`.

```sh
python3 ${HERMES_SKILL_DIR}/scripts/on_this_day.py stage \
  --state-dir <temporary-state-directory> \
  --selection <temporary-selection-file>
```

For delivery validation, use the returned token and a local PNG or JPEG:

```sh
python3 ${HERMES_SKILL_DIR}/scripts/on_this_day.py publish \
  --state-dir <temporary-state-directory> \
  --image <local-test-image> \
  --image-token <token> \
  --dry-run
```

These commands do not use the profile model, generate an image, or send Telegram messages. Never reset production delivery markers for tests.
