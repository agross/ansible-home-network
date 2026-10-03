# Issue tracker: GitHub

Issues and specs live in GitHub Issues for `agross/ansible-home-network`.
Use the `gh` CLI for tracker operations.

## Conventions

- Create: `gh issue create --title "..." --body-file <file>`.
- Read: `gh issue view <number> --comments`.
- Read structured details:
  `gh issue view <number> --json number,title,body,labels,comments,state,assignees`.
- List: `gh issue list --state open --json number,title,body,labels,assignees`.
  Apply label and state filters as needed.
- Comment: `gh issue comment <number> --body-file <file>`.
- Update body: `gh issue edit <number> --body-file <file>`.
- Apply or remove labels:
  `gh issue edit <number> --add-label "..." --remove-label "..."`.
- Claim: `gh issue edit <number> --add-assignee @me`.
- Close completed work: `gh issue close <number> --reason completed`.

Run inside the clone so `gh` infers the repository. Otherwise pass
`--repo agross/ansible-home-network`.

For multiline bodies and comments, save the exact Markdown to a temporary
file and pass it with `--body-file`. Verify published changes by reading
the issue back.

When a skill says "publish to the issue tracker", create a GitHub issue.
When it says "fetch the relevant ticket", read the issue and its comments.

GitHub shares a number space across issues and pull requests. If a ticket
reference resolves to a pull request, use the corresponding `gh pr`
commands.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Wayfinding operations

Used by `/wayfinder`. A map is one issue with child issues as tickets.

- Map: create an issue labelled `wayfinder:map`, containing Notes,
  Decisions-so-far, and Fog.
- Child: link it to the map using GitHub sub-issues. If unavailable, add
  the child to a task list in the map and put `Part of #<map>` at the top
  of the child body.
- Child labels: `wayfinder:research`, `wayfinder:prototype`,
  `wayfinder:grilling`, or `wayfinder:task`.
- Blocking: use GitHub native issue dependencies. If unavailable, put
  `Blocked by: #<number>` at the top of the child body.
- Frontier: choose the first open child in map order with no open
  blockers and no assignee.
- Claim: assign the child to the driving developer.
- Resolve: comment with the result, close the child, then append a brief
  result and link to the map's Decisions-so-far.
