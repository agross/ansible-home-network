---
name: site-presence
description: Resolve Alex and Sonja's home or garden presence.
version: 0.1.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [iobroker, presence, home, garden]
---

# Site Presence

Use current ioBroker states when a request depends on whether Alex or Sonja is
at home or in the garden (OGD). Presence is a fresh fact, never chat context.

## When to Use

- A request refers to Alex or Sonja arriving, being home, or being at the garden.
- The target site determines a follow-up action, such as a reminder or a list.
- Don't use for historic location questions without a requested live check.

## Prerequisites

The `iobroker-home` and `iobroker-ogd` MCP servers must be enabled. Each must
expose a state-reading tool.

## Procedure

1. Choose the person: `alex` is Alex; `sonja` is Sonja. If the request does not
   identify a person and the choice affects the action, ask who it concerns.
2. Read `ping.0.iobroker.mobile-phone-<person>` from both MCPs: `iobroker-home`
   for home and `iobroker-ogd` for garden. Use the current tool schema; do not
   infer presence from a prior result.
3. Interpret a boolean `true` as present at that MCP's site. Report `home`,
   `garden`, or `away` when both values are false.
4. When both are true or a read fails, report the state as unresolved and ask
   for the intended site before an action whose destination depends on it.

## Pitfalls

- OGD means the garden site, not a room at home.
- A remembered or earlier-message location is not a presence result.
- Do not expose ioBroker credentials or raw MCP configuration in replies.

## Verification

State the person, the resolved site, and that both site states were read during
this request. For an unresolved result, confirm that no site-dependent action
was taken.
