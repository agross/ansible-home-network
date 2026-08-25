# Renovate PR Reviews

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
