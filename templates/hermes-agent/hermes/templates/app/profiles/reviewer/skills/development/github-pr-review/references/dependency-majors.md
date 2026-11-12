# Dependency major upgrades

On dependency major-version upgrades (e.g., Go module `/vN` path bumps), verify
that source imports are updated across the codebase and the old major version
is removed from the manifest (`go.mod`/`go.sum`). Automated dependency bots often
add the new module requirement without rewriting import paths, leaving the new
dependency unused and `go mod tidy` dirty while CI still passes against the old
version. Read applicable repository review guidance and check relevant release
notes and migration requirements before publishing findings.
