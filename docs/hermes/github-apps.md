# Hermes GitHub Apps

The `developer` and `reviewer` profiles use separate GitHub App identities.
Each app can be installed on multiple accounts or organizations. See
[the GitHub workflow](github-workflow.md) for handoffs.

## App settings

| Setting | Developer | Reviewer |
| --- | --- | --- |
| Configured app slug | `developer` | `reviewer` |
| Webhook URL | `https://hooks.hermes.therightstuff.de/p/developer/webhooks/developer-github` | `https://hooks.hermes.therightstuff.de/p/reviewer/webhooks/reviewer-github` |
| Subscribed events | Issues, Issue comment, Pull request, Pull request review | Pull request |
| Profile workspace | `/opt/data/profiles/developer/workspace` | `/opt/data/profiles/reviewer/workspace` |
| Container private key path | `/opt/data/profiles/developer/github-app.pem` | `/opt/data/profiles/reviewer/github-app.pem` |

Set a distinct webhook secret for each app. Add each app's client ID, webhook
secret, and owner-to-installation-ID mapping under
`vault_hermes_profile.developer.github` or `vault_hermes_profile.reviewer.github`
in the Hermes host vault. Slugs are set in `host_vars/hermes/hermes-agent.yml`;
client IDs, installation IDs, and webhook secrets are supplied through the
vault. The reviewer also uses its own `vault_hermes_profile.reviewer.opencode_go.api_key`.

The local PEM files are sourced from the matching profile directories under
`templates/hermes-agent/hermes/templates/app/profiles/`; the copy task deploys
these files with profile ownership and mode `0600`. Keep private keys and
webhook secrets out of documentation and version control.

Each route accepts only installation IDs in that profile's mapping. This
limits webhook admission, not individual senders or use of the app private
key. GitHub installation scope controls repository access.

## Repository permissions

Set these under **Permissions & events → Repository permissions** for each
GitHub App. Install both apps on each account or organization and grant access
to the repositories they should handle. The developer and reviewer use
separate installations and credentials.

| Repository permission | Developer | Reviewer | Purpose |
| --- | --- | --- | --- |
| Actions | Read-only | Read-only | Inspect GitHub Actions runs and logs. |
| Checks | Read-only | Read-only | Inspect check runs and results. |
| Commit statuses | Read-only | Read-only | Inspect commit status results. |
| Contents | Read and write | Read-only | Clone and read code; the developer also pushes branches. |
| Issues | Read and write | Read and write | Read issues and comments; manage issue/PR labels and opening-post reactions. The developer also assigns the PR to the issue author. |
| Metadata | Read-only | Read-only | Repository metadata; GitHub grants this automatically. |
| Pull requests | Read and write | Read and write | Read PRs and feedback; the developer creates and updates PRs, and the reviewer submits reviews. |
| Workflows | Read and write **if needed** | No access | The developer needs this additional permission when work modifies files in `.github/workflows`. |

The reviewer does not need Contents write: it reads code and posts reviews,
but does not push changes. Actions read is separate from Workflows write;
reading CI runs does not require permission to modify workflow files.

## Webhook subscriptions

Enable each app's webhook using the URL and secret above, and subscribe to
these events:

| App | Events | Repository permission needed for subscription |
| --- | --- | --- |
| Developer | Issues; Issue comment; Pull request; Pull request review | Issues read and Pull requests read, already covered by the write permissions above. |
| Reviewer | Pull request | Pull requests read, already covered above. |

The developer route handles `labeled` actions for issues and PRs, new human
comments on issues, and `submitted` pull request reviews. For an issue comment,
the developer re-fetches the issue and comment, checks `ready-for-agent` is
still present, and verifies the commenter has repository write or admin access.
The reviewer route handles `opened`, `reopened`, `ready_for_review`, and
`synchronize` pull request actions. A
PR conversation comment alone does not trigger the developer route. Each route
also filters on its configured installation IDs.

The apps' own webhooks do not require the repository **Webhooks** permission;
that permission is for managing repository webhooks. Grant additional
permissions only for explicitly needed work, such as editing GitHub Actions
workflow files. Repository rules, branch protection, fork access, and
assignability still apply even when the app has these permissions. If an
installation already exists, its owner may need to approve permission changes.

Sources: [GitHub App permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps),
[choosing permissions](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app),
and [webhook events](https://docs.github.com/en/webhooks/webhook-events-and-payloads).

## Container configuration

Compose builds `nousresearch/hermes-agent:v0.22.7-custom` using
`docker/Dockerfile`. The image checks out the pinned plugin revision and copies
`docker/__init__.py` into the plugin directory. It installs the CLI wrappers
from the same checkout in `/opt/github-app`; Hermes installs its plugin
runtime dependencies when the plugin is enabled. Both webhook routes include
the `github_app` toolset.

Enable the bundled `github-app` plugin in Hermes before using its native tools.
The `plugins.enabled` setting selects the plugin but does not by itself prepare
its Python dependencies. On a fresh installation, if Hermes reports the plugin
already enabled but `hermes-github-app` is unavailable, bootstrap the affected
profile on the `hermes` host:

```sh
hermes --profile developer plugins disable github-app
hermes --profile developer plugins enable github-app
```

Use `reviewer` in place of `developer` for that profile. Restart the gateway
when prompted, then run the profile-aware doctor below. The disable step makes
the next enable a state change: Hermes's enablement transaction then prepares
the dependency environment. Disabling alone does not install dependencies.
An already-enabled plugin skips that transaction, even when dependencies are
missing. Ansible manages profile configuration, so a later deployment restores
the configured enabled state; repeat the bootstrap only when its runtime
dependencies have not been prepared.

The developer uses OpenAI Codex `gpt-6.1-sol`. The reviewer uses OpenCode Go
`gemini-4-argon`, with `glm-5.3-flash` as fallback. These are template settings,
not proof of a running deployment.

## Verification and cutover

After deploying, run the plugin command through Hermes on the `hermes` host
to select a profile:

```sh
hermes --profile developer hermes-github-app doctor --repo OWNER/REPO
hermes --profile reviewer hermes-github-app doctor --repo OWNER/REPO
```

Run each command for a repository in every installation. Use `status` in
place of `doctor` to check the app identity. Test a signed delivery to each
URL and verify the selected profile, installation filter, and resulting
session. Test the developer-to-reviewer feedback loop before disabling old
repository webhooks; overlapping old and new hooks can start duplicate work.
Existing profile skills are not overwritten by the deployment copy task, so
previously deployed skills need a separate update to receive changes.
