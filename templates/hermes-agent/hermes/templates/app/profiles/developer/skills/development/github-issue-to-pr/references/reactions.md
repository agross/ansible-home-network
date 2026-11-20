# Opening-post reactions

After the selected issue or PR passes the parent skill's authorization gate and has
authorized actionable work (repair or clean handoff for a PR), add an
👀 (`eyes`) reaction to its opening post before implementation or feedback
handling. Use the repository and issue or PR number fetched through GitHub:

```sh
gh-app --repo OWNER/REPO -- api --method POST repos/OWNER/REPO/issues/NUMBER/reactions --raw-field content=eyes
```

The issue reactions endpoint also covers PR opening posts. An existing
reaction from the authenticated account counts as success. On an issue,
remove that account's previous 🚀 (`rocket`) reaction when work restarts.
For PR feedback, clear that account's previous 👍 (`+1`) and 👎 (`-1`)
reactions so they cannot imply a review verdict for work in progress.
Skipped or unauthorized events receive no reaction. Report reaction failures
and continue the authorized work.

To remove a reaction, identify the authenticated account with `gh-app --repo OWNER/REPO -- api "users/APP_SLUG%5Bbot%5D"`,
list all opening-post reactions with
`gh-app --repo OWNER/REPO -- api --paginate repos/OWNER/REPO/issues/NUMBER/reactions`, and delete only
matching reactions whose `user.id` equals that account's ID:

```sh
gh-app --repo OWNER/REPO -- api --method DELETE repos/OWNER/REPO/issues/NUMBER/reactions/REACTION_ID
```

Preserve other users' reactions. Verify each completed reaction transition
by fetching the opening-post reactions again. When extracting a reaction ID,
use a JSON parser available in the runtime (for example, `python3` with the
standard `json` module when `jq` is unavailable), and fail if parsing fails;
do not let a failed pipeline parser silently skip deletion.

## Complete work

After initial issue delivery passes final-commit CI, replace this account's eyes
reaction on the issue with `rocket`. Failed or incomplete delivery receives no
rocket.

After a repair or clean handoff, remove this account's eyes reaction from the PR.
Fetch reactions immediately before deletion and use only a freshly fetched ID;
concurrent automation can remove or replace it. A fresh read proving absence
counts as completed cleanup. Verify absence afterward. The reviewer owns the
PR's thumbs-up and thumbs-down outcome reactions.
