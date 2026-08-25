# Ansible Home Network

This is a collection of Ansible roles used to provision machines and services
running in my networks at the `home` and `OGD` sites.

## Project Setup

Run `bootstrap` after checkout or when `requirements.yml` changes.

## Ansible

* Use fully-qualified modules, e.g., `ansible.builtin.file` instead of `file`.
* Use fully-qualified filters, e.g., `ansible.builtin.mandatory` instead of `mandatory`
* Jinja-builtins can be used in short form, e.g., `map`.
* End prose comments with a dot (`.`). Preserve machine-readable directives
  such as `# renovate:` and `# noqa`.
* Put `when` before the module name.
* Put the following keys after the module:
  * `loop`,
  * then `vars`,
  * then `register`,
  * then `failed_when`.
* NEVER run `ansible-playbook` against hosts. You can use it to syntax-check,
  but NOTHING else.
* Do not use `---` at the beginning of YAML files.

## Agent skills

### Renovate reviews

Before reviewing, commenting on, or editing a Renovate dependency PR, read
`docs/agents/renovate-review.md`.

### Issue tracker

Before creating, claiming, updating, or closing work, read
`docs/agents/issue-tracker.md`.

### Domain docs

Before changing domain vocabulary or ADR-governed behavior, read
`docs/agents/domain.md`.
