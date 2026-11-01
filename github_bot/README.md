# GitHub bot helper

Repository-scoped GitHub App operations using Python 3.9+, OpenSSL, and Git.
This is the maintained copy of the local helper, bundled with the workflow so
projects can pin code, instructions, and validation together in one submodule.

## Settings without a config file

The bundled helper no longer reads config.json or accepts --config. Store the
nonsecret App ID, installation ID, repository, and reviewer settings in the parent
project's AGENTS.md. The agent reads those settings and passes CLI arguments; the
helper intentionally does not parse arbitrary Markdown. Confirm the repository
against origin and resolve the actual checkout path, including worktrees.

The private key remains a local file outside repositories. The user supplies its
absolute path in chat; the agent sets `GITHUB_APP_PRIVATE_KEY_PATH` on each helper
process. The user does not need to export anything. Reuse a valid existing variable
or a path already supplied in the conversation; ask only when neither is available
or the path is invalid. Providing the path for bot use authorizes this process-scoped
setup without another confirmation. Never request or pass key contents. Do not
persist the path in AGENTS.md, config files, or shell startup files.

Example agent invocation with a command-scoped variable (replace example values):

```sh
GITHUB_APP_PRIVATE_KEY_PATH='/absolute/path/to/github-app.pem' \
python3 .agent-workflow/github_bot/github_bot.py \
  --app-id 123 --installation-id 456 \
  --repo OWNER/REPO --checkout /absolute/path/to/parent-project check
```

The IDs are identifiers, not secrets. They cannot be derived from the private key
or repository URL alone; obtain and approve them during setup. The app installation
must have access to each project. For an authorized workflow-source fetch, use its
repository and absolute submodule checkout with the appropriate installation ID.

No credentials or machine-specific key path are committed here. Missing settings
fail before authentication with a clear error; the helper never falls back to a
config file, personal credentials, or another installation.

This change applies only to this bundled helper. Existing external installations
such as ~/tools/github_bot are not modified and may still use --config. Adopt the
new helper and matching instructions together through an explicit workflow upgrade.

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

GitHub controls notification delivery. Review re-requests use the documented GraphQL `rerequestReviews` mutation with
reviewer node IDs resolved using the installation token. The REST `/rerequest`
endpoint repeatedly returned HTTP 500 for a pending reviewer; the GraphQL path
succeeded live on 2026-11-01 with the same App installation and PR. GitHub's internal
cause of the REST failure is unknown. No permission changes are required.

The helper requires both a successful mutation response for the correct PR and
confirmed requested-reviewer state. Existing pending state alone is not proof of a
new notification. It never removes other reviewers or automatically retries or
falls back after an ambiguous write. GraphQL errors are sanitized. Successful API
acceptance does not prove email or inbox delivery.

## Tests

```sh
python3 -m unittest discover -s github_bot -v
```

Tests use fake API sessions and a disposable local Git repository. They do not use
real credentials or GitHub writes. The copied helper has 47 tests covering identity,
credential isolation, ready/stack validation, requests/re-requests, CLI parsing,
permission reporting, CI reads, and PR editing.

[GitHub review request API](https://docs.github.com/en/rest/pulls/review-requests)

The bundled copy also authenticates its bot-identity lookup with the scoped
installation token, avoiding the unauthenticated lookup that returned HTTP 403.
It revokes the token if that lookup fails. Tests cover the authenticated call and
cleanup on failure; success against GitHub must still be verified separately.

## Diagnosing authentication and rate limits

The private key signs an app JWT. The JWT authenticates the app while it requests
an installation token scoped to the selected repository. Repository requests and
the bot-user lookup use that installation token; the private key is never sent to
GitHub. Merely having a key does not authenticate a request without its header.

The user lookup runs after token creation and uses that token. Any failure after
token creation attempts revocation; local token state is cleared even when
revocation fails, and cleanup errors do not replace the original failure.

HTTP diagnostics show the method, endpoint, status, whether authentication was
sent, and bounded numeric rate-limit headers (limit, remaining, reset_epoch, and
retry_after_seconds). They never print the response body, Authorization header,
JWT, token, private key, or arbitrary response headers. A 403/429 with remaining=0
identifies primary rate exhaustion. Retry-After/429 reports throttling. A 403 with
no supporting headers remains ambiguous; it does not establish missing permissions.
Honor backoff headers and do not automatically retry mutations.

A failure at GET /users/<bot> is session initialization failure, before any
/stacks endpoint. Do not change stack permissions on that evidence. Check which
helper path the agent actually executed; older local or pinned copies can retain
the unauthenticated lookup. This repository's helper and the maintained external
local copy now use authenticated lookup. Other submodule pins need explicit updates.

43 offline tests pass, including lookup order/token use, token cleanup on failure,
safe rate-limit diagnostics, malformed-header rejection, and existing stack tests.

Six additional tests cover config-free argument/environment setup, missing/invalid
IDs and key paths, rejection of --config, no config-file reads, and credential
helper compatibility.

[GitHub GraphQL review re-request](https://docs.github.com/en/graphql/reference/pulls#rerequestreviews)

Review commands reuse reviewer identities from the current PR response when
available. An already-pending ordinary request needs only the initial PR read;
actual writes still receive a fresh verification read. No persistent cache is used.
