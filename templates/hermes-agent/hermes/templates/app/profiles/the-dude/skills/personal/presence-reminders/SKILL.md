---
name: presence-reminders
description: Deliver pending home or garden reminders when Alex or Sonja is present.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [iobroker, reminders, Telegram, blueprint]
    blueprint:
      schedule: "0 9-22 * * *"
      deliver: telegram
      prompt: "Hourly from 09:00 through 22:00 Europe/Berlin, run presence-reminders. Query the configured ioBroker presence states, return each due reminder line once as the final response (delivered via Telegram automatically); do NOT use send_message. BEFORE returning, atomically rewrite reminders.json keeping only the reminders that are not due this turn, so delivered lines are removed in the same turn. If none are due, neither send nor rewrite, and return [SILENT]."
      no_agent: false
---

# Presence Reminders

The blueprint runs hourly from 09:00 through 22:00 Europe/Berlin when the
profile timezone is Europe/Berlin. It requires the configured `iobroker-home`
and `iobroker-ogd` MCPs.

Pending reminders live in `${HERMES_HOME:-~/.hermes}/workspace/state/presence-reminders/reminders.json`:

```json
{
  "alex": {"home": ["..."], "garden": ["..."]},
  "sonja": {"home": ["..."], "garden": ["..."]}
}
```

For each person and location, query the matching ioBroker state
`ping.0.iobroker.mobile-phone-alex` or `ping.0.iobroker.mobile-phone-sonja`
through `iobroker-home` for home and `iobroker-ogd` for garden. A true value
means present.

Read the state file privately. Matching is strictly per (person, location) key:
a reminder under `alex.garden` may only be delivered when the ioBroker-OGD state
for Alex reads `true`; a reminder under `alex.home` only when the ioBroker-home
state for Alex reads `true` (same for Sonja). A reminder whose location key does
NOT match the person's current true-site must never be delivered — in
particular, a garden reminder is never delivered while the person is not read
as present at the garden, and a home reminder is never delivered while the
person is not read as present at home.

For every (person, location) key where the ioBroker state for that exact key is
`true` and that key's list is non-empty, form one German line per reminder:
`🏠 Alex ist zuhause! Erinnerung: …`, `🌳 Alex ist im Garten! Erinnerung: …`,
`🏡 Sonja ist zuhause! Erinnerung: …`, or `🌿 Sonja ist im Garten! Erinnerung: …`.

**Removal happens in the same turn as the send, not after delivery.** The cron
agent has no way to verify the gateway's later Telegram call, so a post-delivery
removal never runs. Therefore: BEFORE returning the response, rewrite the state
file atomically (temp file write + `os.replace`) keeping only the reminders that
are NOT due this turn. A reminder is due only when its (person, location) key's
ioBroker state read `true` this turn — remove exactly those due lines and keep
every reminder whose site read was false, failed, or uncertain. In other words,
every line about to be returned as text is removed from the file in the same
turn, and nothing else is touched. Return `[SILENT]` if no (person, location)
key is both present and non-empty.
