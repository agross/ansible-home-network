---
name: location-aware-shopping
description: Manage shopping lists at Alex's current site.
version: 0.1.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trello, shopping, iobroker, garden]
---

# Location-Aware Shopping

Manage Alex's Trello shopping list at the site where he currently is. A request
such as "Add milk to the shopping list" authorizes that list change; resolve
the current site with ioBroker immediately before choosing the Trello board.

## When to Use

- Add, remove, check, show, or reconcile a shopping-list item.
- Create a shopping list from a recipe or meal request.
- Don't use for ordinary Trello project cards that are not shopping lists.

## Prerequisites

The `iobroker-home`, `iobroker-ogd`, and `trello` MCP servers must be enabled.
Use their exposed tool schemas; credentials remain in Hermes configuration.

## Procedure

1. Read Alex's current garden state from `iobroker-ogd` for
   `ping.0.iobroker.mobile-phone-alex`. Read the matching home state from
   `iobroker-home` as a presence check. Do this for every request; never reuse
   a prior location.
2. If the garden state is `true`, select the Trello board named `OGD`. If it is
   `false` and the home read succeeds, select `Personal Kanban`. If either read
   fails or both states are `true`, stop and ask Alex for the destination.
3. Inspect only non-Done cards on the selected board. At `Personal Kanban`, use
   the `Pantry` card and its `Einkauf` checklist. At `OGD`, use the active card
   and checklist for `Einkauf`; if several candidates exist, ask rather than
   guessing. Done-column cards are history, not shopping lists.
4. Before adding an item, compare open checklist entries case-insensitively and
   ignore surrounding whitespace. If it already exists, report that fact without
   adding a duplicate. Otherwise add the requested wording as one checklist item.
5. Before checking or removing an item, identify the exact open checklist entry.
   Apply the requested change only to that entry.
6. Re-read the selected checklist. Confirm the requested item has the expected
   open or completed state, then report the board, card, and checklist used.

## Pitfalls

- Garden `true` selects `OGD`; do not choose a board from message context.
- A false garden state does not prove a working home read. Treat failed or
  contradictory presence reads as unresolved.
- Do not use a card in Trello's Done column for "shopping yesterday"; only open
  items in the active `Einkauf` checklist count.
- Preserve quantities and qualifiers in the requested item name.

## Verification

For every mutation, report the freshly read presence result, target board,
active card and checklist, and the result of the checklist re-read. If the
site or list is unresolved, confirm that Trello was not modified.
