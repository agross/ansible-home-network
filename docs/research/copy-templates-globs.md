# Glob matching for copy-templates settings

Implemented after approval: `test_plugins/globmatch.py` uses case-sensitive `PurePosixPath.full_match` (controller Python 3.13+), checks directory-only trailing slashes, and reserves the empty path for an explicit root entry. All three tasks use it. Traefik hooks retain mode `750` through explicit empty-root and `**/*` entries. Seven local regression tests cover matching, actual Ansible settings evaluation, Hermes permissions, Traefik permissions, and filetree loops. No deployment was performed.

The assessment below records the pre-change behavior and design rationale.

## Current behavior

`tasks/copy-templates.yml` enumerates directories and files using `community.general.filetree`. The `files` mapping supplies settings; it does not select which files are copied. Each of the three tasks uses an exact source-relative path first, then the first matching pattern, then defaults. Template matching includes the `.j2` suffix. `test_plugins/fnmatch.py` delegates to Python's `fnmatch.fnmatch`, which does not treat `/` specially.

## Proposed approach

Keep filetree discovery and precedence. Replace the custom test with a pathname-aware glob test in all three tasks. On controller Python 3.13 or newer, `PurePosixPath(path).full_match(pattern)` provides whole-path matching with recursive `**`. Use explicit case-sensitive matching for stable behavior. Do not use `PurePath.match`, which matches relative patterns from the right and does not implement recursive `**`.

Handle a trailing `/` explicitly: require `item.state == 'directory'`, strip the trailing separator, then match. Pathlib normalization alone cannot enforce directory-only matching. Preserve dotfile matching and define the synthetic root (`item.path == ''`) explicitly; an exact empty-string key is the clearest root override. Older controller Python versions need a compatible matcher or filesystem expansion instead.

`ansible.builtin.fileglob` is not a direct replacement: it only matches files in a single directory and is non-recursive.

## Existing callers and compatibility

- `roles/hermes-agent/tasks/main.yml:32`: `app/profiles/*/config.yaml.j2` currently also matches deeper descendants. With pathname globs, `*` matches one component; `**` is needed for arbitrary depth.
- `roles/hermes-agent/tasks/main.yml:40`: `app/profiles/*/` currently misses directory paths because filetree returns relative paths without a trailing slash. Explicit directory-pattern handling would fix this.
- `roles/traefik-cert-exporter/tasks/main.yml:19`: `*` currently matches descendants and the synthetic empty root. The accompanying `**/*` covers descendants under recursive glob semantics, but root permissions need an explicit decision.
- Exact-path settings and first-pattern precedence should remain unchanged. Settings should not silently begin merging.

## Local verification

A read-only Python 3.14.7 probe confirmed: a nested profile config matches the old `*` pattern but not `full_match`; `export` matches `**/*` only with `full_match`; the empty path matches `*` only with fnmatch. No playbooks were run. The probe verifies matching primitives, not an implemented Ansible integration.

## Primary sources

- [Python fnmatch](https://docs.python.org/3.13/library/fnmatch.html): path separators are not special.
- [Python PurePath.full_match](https://docs.python.org/3.13/library/pathlib.html#pathlib.PurePath.full_match): recursive whole-path glob matching, added in Python 3.13.
- [Python glob.translate](https://docs.python.org/3.13/library/glob.html#glob.translate): alternative regex translation with explicit recursive, hidden-file, and separator controls, added in Python 3.13.
- [Ansible fileglob](https://docs.ansible.com/projects/ansible-core/devel/collections/ansible/builtin/fileglob_lookup.html): single-directory, non-recursive file matching.
- [community.general filetree source](https://raw.githubusercontent.com/ansible-collections/community.general/main/plugins/lookup/filetree.py): relative paths are constructed with os.path.relpath, without directory suffixes.
