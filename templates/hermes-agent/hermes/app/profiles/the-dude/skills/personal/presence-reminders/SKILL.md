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
      prompt: "Hourly from 09:00 through 22:00 Europe/Berlin, run presence-reminders. Query the configured ioBroker presence states, send each due reminder once to Telegram, then atomically remove only delivered reminders. If none are due, return [SILENT]."
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

Read the state file privately. For every present person with pending reminders,
form one German line per reminder: `🏠 Alex ist zuhause! Erinnerung: …`,
`🌳 Alex ist im Garten! Erinnerung: …`, `🏡 Sonja ist zuhause! Erinnerung: …`,
or `🌿 Sonja ist im Garten! Erinnerung: …`. Return all due lines. After Hermes
confirms Telegram delivery, remove exactly those delivered lines with an atomic
file replacement. Never remove reminders after a failed or uncertain delivery.
Return `[SILENT]` if nobody is present or nothing is pending.
