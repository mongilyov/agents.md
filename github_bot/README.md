# GitHub bot helper

Repository-scoped GitHub App operations using Python 3.9+, OpenSSL, and Git.
This is the maintained copy of the local helper, bundled with the workflow so
projects can pin code, instructions, and validation together in one submodule.

## Configuration

Copy config.example.json to a private location outside repositories, fill the App
and installation IDs and the absolute private-key path, and restrict local access.
The private key must also remain outside repositories. Never commit a real config,
key, or token. The example contains no credentials. Grant the installation access
to each project and to the workflow repository if fetching it as the bot.

Always invoke from the parent project using explicit global arguments:

```text
python3 .agent-workflow/github_bot/github_bot.py \
  --config /absolute/external/path/config.json \
  --repo OWNER/REPO --checkout /absolute/path/to/parent-project <command>
```

The checkout is the parent project, not the workflow submodule. For an explicitly
authorized workflow-source fetch, select `--repo mongilyov/agents.md` and the
submodule's absolute path as `--checkout`. Do not rely on config repository defaults.

## Commands

- `check`: authenticate, confirm single-repository token scope, show grants and
  missing workflow permissions, and verify HTTPS Git read access.
- `fetch`: fetch origin with isolated bot credentials; never merge.
- `commit --message-file PATH`: commit already-staged changes with bot author and
  committer identity, without changing your normal Git identity.
- `push --branch BRANCH`: push only that branch; no force push or automatic merge.
- `create-pr --ready --head BRANCH --base BASE --title TITLE --body-file PATH`:
  create a ready PR. Use the preceding stack branch as BASE for dependent PRs.
  The script retains draft-by-default behavior for compatibility: always pass
  `--ready` unless the user explicitly requests a draft.
- `edit-pr --pr NUMBER [--title TITLE] [--body-file PATH]`: update supplied fields.
- `ready --pr NUMBER`: mark an existing draft ready, with read-back verification.
- `pr --pr NUMBER`: read an open PR and requested reviewers.
- `checks --pr NUMBER`: read check runs, statuses, and Actions runs for its head.
- `comments --pr NUMBER`: read conversation comments, inline comments, and reviews.
- `reply --pr NUMBER --body-file PATH`: post a conversation comment.
- `reply --pr NUMBER --review-comment-id ID --body-file PATH`: reply inline.
- `request-review --pr NUMBER --reviewers LOGIN [LOGIN ...]`: request users' reviews;
  already-pending requests are a no-op.
- `request-review --pr NUMBER --reviewers LOGIN [LOGIN ...] --rerequest`: send a fresh
  review request once after a verified feedback batch. Do not retry ambiguous writes.
- `stack --prs NUMBER NUMBER [...]`: register open dependent PRs in bottom-to-top
  order as a native GitHub stack. Existing exact membership is a no-op; different or
  extended membership is refused, not silently replaced. Register the complete
  intended stack once its PRs exist; report API limitations instead of improvising.

Use only supported CLI commands for GitHub operations. Do not import helper
internals, run ad-hoc API scripts, use gh/curl/browser writes, or use personal
credentials. Local Git inspection, staging, and branching may use Git directly.
The helper does not currently clone repositories, initialize submodules, change PR
bases, or force-push rebased stacks. Report unsupported operations rather than
bypassing it. One-time submodule initialization is documented as human setup.

## Authentication and limitations

App JWTs are signed by OpenSSL. Each invocation obtains a token scoped to the
selected repository, keeps it out of Git config and disk, and revokes it on exit.
The credential helper validates host and repository; Git tracing is disabled and
token output redacted. Origin must match for commits, pushes, and fetches.

Grants required for this workflow: Metadata:read, Contents:write,
Pull requests:write, Checks:read, Actions:read, Statuses:read. Workflow-file changes
may additionally require Workflows:write. Branch protections still apply. Actual
access must be checked; missing CI access or no check runs is not a passing build.

GitHub controls notification delivery. Review re-requests use the documented
notification endpoint; after HTTP errors, report uncertainty instead of claiming
success or automatically retrying. On 2026-11-01 a live re-request returned HTTP 500;
this remains an external failure, not a passing live notification test.

## Tests

```sh
python3 -m unittest discover -s github_bot -v
```

Tests use fake API sessions and a disposable local Git repository. They do not use
real credentials or GitHub writes. The copied helper has 29 tests covering identity,
credential isolation, ready/stack validation, requests/re-requests, CLI parsing,
permission reporting, CI reads, and PR editing.

[GitHub review request API](https://docs.github.com/en/rest/pulls/review-requests)

The bundled copy also authenticates its bot-identity lookup with the scoped
installation token, avoiding the unauthenticated lookup that returned HTTP 403.
It revokes the token if that lookup fails. Tests cover the authenticated call and
cleanup on failure; success against GitHub must still be verified separately.
