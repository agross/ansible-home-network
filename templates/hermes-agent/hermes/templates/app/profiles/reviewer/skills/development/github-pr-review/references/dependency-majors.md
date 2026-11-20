# Dependency major upgrades

On dependency major-version upgrades (e.g., Go module `/vN` path bumps), verify
that source imports are updated across the codebase and the old major version
is removed from the manifest (`go.mod`/`go.sum`). Automated dependency bots often
add the new module requirement without rewriting import paths, leaving the new
dependency unused and `go mod tidy` dirty while CI still passes against the old
version. Read applicable repository review guidance and check relevant release
notes and migration requirements before publishing findings.

Map each documented breaking API change to every pinned call site, including
namespace imports and dependency-registration code. When a release removes a
runtime default (such as reflection-based serialization), trace each client
construction path and require an execution test of that path; a successful build
cannot prove its runtime configuration supplies the newly explicit dependency.
When an upgrade relocates an instance overload to an extension method, verify
that callers import the extension's declaring namespace (or use the replacement
API); otherwise a lockfile-only update can leave the project uncompilable.

For a .NET CLI tool upgrade whose release changes supported runtimes, inspect the
pinned consumer before accepting the update: find each `dotnet tool restore` and
tool invocation, then compare the documented tool runtime floor with the SDK
selected by `global.json` and any shared target framework in `Directory.Build.props`.
Use the workflow's actual setup step as compatibility evidence, because project
TFMs alone do not prove the formatter or analyzer can start in CI.

For a NuGet major upgrade under Central Package Management, inspect the exact
`.nupkg` nuspec after identifying every direct consumer and every central pin for
its dependency family. Extract the nuspec directly from the downloaded package
with a standard-library ZIP/XML probe when a dedicated archive utility is not
available; this preserves the artifact-to-dependency evidence without depending
on host tooling. Also inspect separately pinned companion packages that consume
the upgraded package: compare their nuspec dependency versions with the new
central pin and inspect the matching companion major when it is published.
Treat an exact or incompatible companion dependency as a required aligned upgrade
and lock regeneration even if compilation or cached CI succeeds, because a direct
central resolution can mask an incoherent runtime package graph. Compare the
package's minimum dependency versions against those pins, then use the failed
restore log to confirm any downgrade; a package can resolve from the registry
while CPM forces an incompatible transitive dependency.
