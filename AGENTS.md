# Shared engineering workflow

These rules apply to projects whose root AGENTS.md explicitly references this file.
Project settings live in that root file. Resolve project-relative paths there;
this submodule is the shared source, not the project checkout.

When maintaining the standalone mongilyov/agents.md source repository itself,
the downstream setup gate and project settings do not apply. Follow the engineering
rules below and the maintenance instructions in README.md; do not fill template
placeholders with this source repository's settings.

## Setup gate: before any repository work

- Read the parent project’s AGENTS.md and this shared workflow first. If setup is not confirmed or any project setting is unfilled, explicitly ask the user to complete and approve the settings before starting any other repository work. Do not silently infer and fill them.
- Until approval, only discuss setup and read these instruction files. Read other files to propose settings only with the user's permission. Edit settings only when authorized, and change `Setup confirmed` to `yes` only after explicit user confirmation.
- This gate precedes planning, fetching, branching, implementation, testing, commits, and publishing. Bypass it only when the user explicitly says to, for the stated scope; do not treat an ordinary task request as a bypass or silently mark setup confirmed.
- Once setup is confirmed, use it on subsequent tasks without asking again unless required settings become missing or invalid.

## Adopt, synchronize, and upgrade

- Keep project settings and project-specific conventions in the parent AGENTS.md (or linked project documents). Read shared rules from `.agent-workflow/AGENTS.md`; do not copy them into the parent file. Discuss conflicting project rules with the user before changing them.
- Treat `.agent-workflow` as read-only during project work. Shared rule or helper changes belong in a separate upstream PR. The parent's submodule pointer records the workflow version; no duplicate revision field or copy-comparison validator is needed.
- Bootstrap on a setup branch: add the submodule at an approved commit, copy `templates/AGENTS.md` only if no root instructions exist, then fill project settings with explicit user approval. Existing instructions require an agreed migration, not blind replacement. A setup-gate bypass must be explicitly authorized and limited to bootstrap. Preserve existing specifications, plans, work, and PR relationships.
- Whenever pulling a project, include submodules: use `git pull --ff-only --recurse-submodules`. Inspect the working tree first; do not force, discard changes, or merge diverged history automatically. This is synchronization to the project's recorded pins, not an upgrade to upstream's latest workflow. Do not pull automatically at task startup.
- Agents must keep GitHub access bot-only. The current helper has `fetch`, not `pull`: use helper-authenticated fetches for the parent and initialized submodules, an authorized local fast-forward to the intended fetched branch, then `git submodule update --init --recursive --no-fetch --checkout`. If initialization or missing objects need unsupported network operations, ask for human initialization rather than bypassing the helper. Human pulls use the recursive command above.
- When the user requests a workflow upgrade, review the upstream changes and select a reviewed commit. Fetch with the current trusted helper, check out that commit detached in the clean submodule, and read the updated rules. Verify helper changes before running them with credentials. Ask for approval of any newly required project settings.
- Publish the workflow bump as a dedicated parent-project PR: normally only the `.agent-workflow` pointer changes. Include old/new commits, what changed, why, and verification. Change the root AGENTS.md only if project settings or its link need updating. Do not rewrite shared rules into it.
- A workflow-bump PR may be the bottom of an authorized feature stack if the feature depends on it; otherwise keep it independent. Do not automatically rebase or retarget unrelated open PRs. Ordinary feature work does not authorize changing the workflow pin.

## Understand first

- Read the relevant code, tests, and project documentation before editing. Reuse proven examples and applicable project skills or scripts.
- Define the intended behavior and how to verify it. For substantial work, outline a short plan with small, independently verifiable steps.
- Follow existing architecture and conventions. Resolve questions from the repository first; ask when missing information would materially change the solution.
- For architectural changes, explain the boundaries and trade-offs, then validate one small end-to-end slice before expanding. For migrations, keep a checklist of affected components and flows so none are missed.

## Plan together, implement one selected increment

- Read PROJECT_SPEC.md and, if present, WORK_PLAN.md. The specification defines the intended product; it does not authorize implementing the whole product.
- Discuss the existing work plan with the user before implementation. If it is missing, propose and refine a plan together. Record the agreed plan or revisions in a small documentation PR when publishing is authorized. Planning discussion alone is not authorization to implement.
- Organize WORK_PLAN.md into numbered, named increments containing numbered checkboxes. Each checkbox describes a verifiable outcome, its dependencies, and relevant verification. A checkbox may require several small PRs; it is not a PR-size boundary. Keep each behavior change and its tests together in the same PR.
- Implement the entire increment explicitly selected by the user, working through all its checkboxes in dependency order. Selection authorizes work across that increment, not the full specification. If no increment is selected, ask before implementing.
- Continue across checkboxes and small stacked PRs without waiting for review or merge after each one. Stop for review only after the selected increment is fully implemented and verified and its PR stack is prepared (published when authorized), or when a blocker requires user input. Do not begin another increment without explicit user direction.
- Update WORK_PLAN.md in the PR that completes and verifies a checkbox, changing it from `[ ]` to `[x]`. If several PRs contribute, keep it unchecked until the final contributing PR and identify the contributing PRs when available. On a stack branch, a checkmark means completed by that PR plus its dependencies; on the default branch, it records accepted work after merge. Leave incomplete or unverified work unchecked.
- Discuss necessary plan changes before implementing them. Include agreed minor clarifications in the relevant PR; use a separate plan PR for changes to scope, ordering, or architecture.
- Stack dependent PRs on their predecessors while implementing the selected increment. Preserve unrelated existing work and plan entries.

Example structure:

```markdown
## Increment 01: Connection setup

- [ ] 01.1 Validate connection settings. Verify: valid and invalid settings tests.
- [ ] 01.2 Establish a connection. Depends on 01.1. Verify: connection integration test.
- [ ] 01.3 Report connection failures. Depends on 01.2. Verify: failure-path tests.
```

## Develop with TDD

For every new behavior or bug fix, use the project's test framework and repeat this cycle one behavior at a time:

1. **Red:** Write a focused test for the expected behavior before changing production code. Run it and confirm it fails because the behavior is missing or incorrect, not because of broken test setup.
2. **Green:** Write the smallest implementation that makes the test pass. Run the test and relevant existing tests.
3. **Refactor:** Simplify the code while preserving behavior. Rerun the relevant tests and keep them green.

- For bugs, the first test must reproduce the bug.
- Test observable behavior rather than internal implementation details. Cover relevant boundaries and failure cases; keep tests deterministic.
- Never weaken, skip, or delete a valid test merely to make the suite pass.
- For behavior-preserving refactors, establish passing coverage first; add characterization tests where coverage is missing.
- If no test setup exists, add the smallest suitable setup before implementing behavior. If execution is blocked, report the blocker and do not claim a verified TDD cycle.
- Documentation-only and formatting-only edits do not need new tests. Verify their relevant output instead.

## Keep changes small

- Implement only what the task requires. Prefer clear, simple code over speculative abstractions, dependencies, or defensive machinery.
- Keep unrelated cleanup out of the change and preserve existing user work.
- If multiple agents work in parallel, allow only one writer per checkout; others review or investigate. Give independent writers separate checkouts and build output directories.
- Fix causes, not symptoms. If repeated attempts fail, revisit the evidence and approach before adding more code.

## Deliver minimal, stacked PRs

- Before editing, inspect the working tree and fetch origin through the bot helper's `fetch` command after the setup gate is satisfied. For a new increment, create a new `<agent_name>/` branch using the configured prefix from the current remote integration branch. For dependent PRs, branch from the preceding stack branch. Preserve existing work; never reset, discard changes, or merge unrelated history automatically.
- If origin is missing or fetching fails, report the blocker rather than silently treating a stale branch as current. If existing changes prevent safe branching, use a separate worktree or ask; never move unrelated changes into the new increment.
- Deliver code changes through small PRs. Each PR must have one clear purpose and contain only the smallest coherent change needed to achieve it. Split changes that can be reviewed separately; do not bundle an entire feature into one large PR.
- Before substantial work, outline the PR sequence, dependencies, and verification for each step. Keep a genuinely small task to one PR.
- Stack dependent branches: `master <- <agent_name>/step-1 <- <agent_name>/step-2`. The first PR targets the project's integration branch; each later PR targets the preceding branch, so its diff shows only its own increment. Independent changes target the integration branch directly.
- For two or more dependent PRs, also register their complete intended bottom-to-top order with `stack --prs ...` after creating them, and verify the reported membership. Dependent base branches and native stack registration are both required; do not stack independent PRs. If registration or extending an existing stack is unsupported or fails, retain correct bases and report the blocker instead of claiming a registered stack or bypassing the helper.
- Complete the TDD cycle within each PR. Keep the behavior change and its tests together; do not publish a failing-test-only PR followed by a separate fix. Each step must build and pass relevant tests on top of its dependencies.
- Open each verified small PR ready for review when publishing is authorized, and request review from the reviewers configured in Project-specific settings. Continue the selected increment's stack without waiting for review. Use drafts only when explicitly requested by the user; if verification is blocked, report it instead of silently delivering a draft. Confirm both the ready state and requested reviewers on GitHub.
- In every PR description, include the increment number and name, the checkbox(s) it advances or completes, a short explanation of what changed and why, dependency links, and verification results. Make the stack order obvious. Keep this text concise.
- Apply review fixes to the branch that owns the change, then update dependent branches and rerun affected checks. Keep PR bases and dependency links correct as earlier PRs merge, without duplicating their changes in later diffs.
- After each completed, verified batch of review fixes, push the updates, reply to the relevant review threads when authorized, and re-request the configured reviewers using `request-review --rerequest`. Do this once per affected PR per feedback batch, not after every intermediate commit. Confirm GitHub accepted the request; do not claim delivery of a notification to the user's device.
- Evaluate automated review suggestions against actual requirements and evidence. Fix real issues; avoid speculative changes that only increase complexity.
- Do not merge PRs, enable auto-merge, or push directly to the integration branch. Leave each increment available for human review.

## Verify and finish

- Run the relevant tests, build, and project-required checks. Fix failures caused by the change.
- After pushing, inspect available CI results and address failures caused by the change. Report pending or inaccessible checks explicitly.
- For UI changes, also exercise the affected flow and compare the rendered result with the intended design. Include screenshots or recordings in the PR when they help verify the change.
- For performance changes, measure a baseline and compare the same workload afterward. Report measurements rather than assuming an improvement.
- Review the final diff for correctness, unnecessary complexity, and unintended changes.
- Report what changed, which checks actually ran and their results, and any remaining limitations. Explain significant design decisions and critical data flows briefly, with a small diagram when useful, so the work is easy to review.

## GitHub bot workflow

Use only the configured `github_bot.py` CLI for bot commits and all GitHub
operations, including authenticated reads, fetch, push, PRs, comments, CI lookups,
and review requests. Do not use gh, curl, browser writes, alternate API scripts,
imports of helper internals, or personal credentials. Local Git status/diff/add/branch
operations may use Git directly. Read its configured README.md before first use.

Resolve configured relative paths from the parent project root. Invoke with python3
and explicitly pass the App ID, installation ID, repository, and actual parent checkout
path (including worktrees) before the subcommand. For an authorized source fetch,
select the workflow repository and submodule checkout instead:

```text
python3 <helper-path> --app-id <APP_ID> --installation-id <INSTALLATION_ID> --repo <OWNER/REPO> --checkout <PARENT_CHECKOUT_PATH> <subcommand>
```

There is no config.json and the helper does not parse AGENTS.md itself. The agent
passes the approved nonsecret settings as arguments. Derive the actual checkout
from the working tree and verify origin matches the configured repository.
App and installation IDs cannot be inferred from the private key or origin alone;
ask for them during setup if unknown. Do not guess IDs or silently choose an installation.

The helper uses `GITHUB_APP_PRIVATE_KEY_PATH` when supplied; otherwise it reads
`.github-bot-key-path` from the selected `--checkout` root. That local file contains
only the absolute key-file path on one line, never key contents. The agent manages
this setup; the user does not need to export variables or edit local files.

Reuse the saved path, a valid environment override, or a path already provided in
chat. If none is available or valid, ask the user for the absolute local key-file
path, not the key contents. Once supplied for bot use, verify it exists, add
`/.github-bot-key-path` to the parent project's .gitignore, verify the path file is
ignored and untracked, and write the path there. This task authorizes saving the
path locally without another confirmation. Commit the ignore rule, never the path
file. Do not put the path in AGENTS.md or shell startup files, copy the key into the
project, or search the machine for keys. Ask again only when the saved path is
missing or invalid. New clones/worktrees may need their own local path file.
For operations selecting another checkout (such as a workflow-source fetch), pass
the known path through the helper process environment instead of requiring a second
saved file. Publishing still requires authorization under the user's task.

If the helper is unavailable or settings are incomplete, report the publishing blocker;
do not fall back to personal GitHub credentials.

Commands:
- check: verify authentication, repository access, and workflow permission grants.
- fetch: fetch origin without merging.
- pr --pr NUMBER: inspect the PR, draft state, and requested reviewers.
- checks --pr NUMBER: read checks, statuses, and Actions runs for the current head.
- commit --message-file PATH: commit already-staged changes as the bot.
- push --branch BRANCH: push the named branch.
- create-pr --ready --head BRANCH --title TITLE --body-file PATH:
  create a PR ready for review; add --base PARENT_BRANCH for stacked PRs.
- edit-pr --pr NUMBER [--title TITLE] [--body-file PATH]: update PR metadata.
- ready --pr NUMBER: mark an existing draft ready for review.
- request-review --pr NUMBER --reviewers LOGIN [LOGIN ...]: request and verify review.
- request-review --pr NUMBER --reviewers LOGIN [LOGIN ...] --rerequest:
  send a fresh review request after verified feedback changes.
- stack --prs NUMBER NUMBER [...]: register dependent PRs as a native stack.
- comments --pr NUMBER: read PR comments and reviews.
- reply --pr NUMBER --body-file PATH: post a conversation comment.
- reply --pr NUMBER --review-comment-id ID --body-file PATH:
  reply in an inline review thread.

Creating a ready PR does not request reviewers automatically. Invoke
`request-review` separately. If a required command is missing, stop that operation
and report the blocker; do not bypass the CLI or change the helper without explicit
authorization. Never automatically retry an ambiguous review notification request.

Required grants: metadata:read, contents:write, pull_requests:write, checks:read,
actions:read, statuses:read. Workflow-file changes may additionally need
workflows:write. Run `check` and read actual PR/check results; permission grants
alone do not prove branch protections permit an operation. Missing CI access is
not a passing check.

Use this helper instead of personal GitHub credentials.
Never print private keys or tokens.

Keep PRs small and focused. Base dependent PRs on their predecessor’s
branch so each diff contains only its own increment.
Run relevant checks and include validation in PR descriptions.

Do not merge PRs or push directly to the default branch.
Only push, create PRs, or post replies when authorized by the user’s task.
