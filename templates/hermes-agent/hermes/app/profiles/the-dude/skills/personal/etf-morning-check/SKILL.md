---
name: etf-morning-check
description: Send Alex a weekday morning summary of the configured ETFs.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [finance, ETF, blueprint]
    blueprint:
      schedule: "0 8 * * 1-5"
      deliver: telegram
      prompt: "At 08:00 Europe/Berlin on weekdays, run the etf-morning-check script and send its German summary to Telegram. Report a script failure only if the script cannot produce a summary."
      no_agent: false
---

# ETF Morning Check

The blueprint runs at 08:00 Europe/Berlin on weekdays when the profile timezone is
Europe/Berlin. It is a suggested automation; accept it in Hermes only after
reviewing the destination.

Run `python3 ${HERMES_SKILL_DIR}/scripts/check_etf.py`. Return its output
unchanged. The script reads current prices from Yahoo Finance without
credentials. It always reports both configured ETFs; individual lookup errors
remain visible in the summary.
