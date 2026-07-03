# Ansible Home Network

This is a collection of Ansible roles used to provision machines and services
running in my networks at the `home` and `OGD` sites.

## Project Setup

1. Clone repository
2. Install dependencies (`bootstrap` in the project root)

## Ansible

* Use fully-qualified modules, e.g., `ansible.builtin.file` instead of `file`.
* Use fully-qualified filters, e.g., `ansible.builtin.mandatory` instead of `mandatory`
* Jinja-builtins can be used in short form, e.g., `map`.
* End comments with a dot (`.`).
* Put `when` before the module name.
* Put the following keys after the module:
  * `loop`,
  * then `vars`,
  * then `register`,
  * then `failed_when`.
* NEVER run `ansible-playbook` against hosts. You can use it to syntax-check,
  but NOTHING else.
* Do not use `---` at the beginning of YAML files.

## Codex Review Guidelines

When reviewing Renovate pull requests for dependency upgrades, identify
potential breaking changes in the target versions in the context of the
Ansible role or deployed service affected by the PR.

Use the local filesystem context whenever possible. Read the PR metadata,
changed files, affected roles, diff, release notes, and migration guide
content before writing findings. Inspect affected role files directly,
especially templates, rendered configuration inputs, defaults, handlers,
host vars, group vars, and Docker Compose files.

Focus findings on breaking changes, migration steps, removed or renamed
options, changed defaults, config/schema changes, data migration
requirements, operational downtime, image/runtime requirements, removed API
endpoints, and behavior that could affect this repository's deployment.

Do not list generic release-note items that are not relevant to the deployed
role. If a finding is uncertain, say why and cite the file or setting that
caused the uncertainty. If release notes are available but no relevant
breaking changes are found, say that directly. If no release notes or
changelog are available after checking the PR body and obvious upstream
release pages, say that directly.

PR comments must start with:

```markdown
<!-- codex-renovate-release-review -->
```

Use this structure:

```markdown
## Codex Renovate release review

One short sentence naming the dependency upgrade and affected role or service.

### Potential breaking changes

- Impact.
  Repository context, citing changed files or role files.
  Suggested manual check or mitigation.

### Release notes checked

- Release-note or changelog URL.
```

Do not edit files during a Renovate review unless explicitly asked to fix the
PR.

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

* Dependency-aware: Track blockers and relationships between issues
* Git-friendly: Dolt-powered version control with native sync
* Agent-optimized: JSON output, ready work detection, discovered-from links
* Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

* `bug` - Something broken
* `feature` - New functionality
* `task` - Work item (tests, docs, refactoring)
* `epic` - Large feature with subtasks
* `chore` - Maintenance (dependencies, tooling)

### Priorities

* `0` - Critical (security, data loss, broken builds)
* `1` - High (major features, important bugs)
* `2` - Medium (default, nice-to-have)
* `3` - Low (polish, optimization)
* `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   * `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs via Dolt:

* Each write auto-commits to Dolt history
* Use `bd dolt push`/`bd dolt pull` for remote sync
* No manual export/import needed!

### Important Rules

* ✅ Use bd for ALL task tracking
* ✅ Always use `--json` flag for programmatic use
* ✅ Link discovered work with `discovered-from` dependencies
* ✅ Check `bd ready` before asking "what should I work on?"
* ❌ Do NOT create markdown TODO lists
* ❌ Do NOT use external issue trackers
* ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

<!-- END BEADS INTEGRATION -->
