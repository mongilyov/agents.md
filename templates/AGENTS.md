# Engineering workflow

## Project-specific settings

Fill these in when adopting this template. Replace placeholders with verified
values; use `not applicable` where appropriate. Never store credentials here.

- Repository: `<OWNER/REPO>`
- Integration branch: `<main or other branch>`
- Setup command: `<command>`
- Build command: `<command or not applicable>`
- Focused test command: `<command with test selector>`
- Full test command: `<command>`
- Other required checks: `<lint, typecheck, integration checks, etc.>`
- UI verification: `<launch command and affected-flow verification, or not applicable>`
- Architecture and conventions: `<key constraints and links to repository docs>`
- GitHub bot helper: `<absolute path to github_bot.py on this machine>`
- GitHub bot README: `<absolute path to the helper's README.md>`

Resolve the checkout path from the actual working checkout, including when using
a worktree. Use the repository and integration branch above; do not assume helper
defaults belong to this project. Resolve missing settings from repository evidence
or ask when they block the task. Do not execute placeholder commands.

The sections below are the shared workflow.

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

- Before editing, inspect the working tree and fetch origin. For a new increment, create a new `codex/` branch from the current remote integration branch. For dependent PRs, branch from the preceding stack branch. Preserve existing work; never reset, discard changes, or merge unrelated history automatically.
- If origin is missing or fetching fails, report the blocker rather than silently treating a stale branch as current. If existing changes prevent safe branching, use a separate worktree or ask; never move unrelated changes into the new increment.
- Deliver code changes through small PRs. Each PR must have one clear purpose and contain only the smallest coherent change needed to achieve it. Split changes that can be reviewed separately; do not bundle an entire feature into one large PR.
- Before substantial work, outline the PR sequence, dependencies, and verification for each step. Keep a genuinely small task to one PR.
- Stack dependent branches: `<integration> <- codex/step-1 <- codex/step-2`. The first PR targets the project's integration branch; each later PR targets the preceding branch, so its diff shows only its own increment. Independent changes target the integration branch directly.
- Complete the TDD cycle within each PR. Keep the behavior change and its tests together; do not publish a failing-test-only PR followed by a separate fix. Each step must build and pass relevant tests on top of its dependencies.
- Open each small PR when publishing is authorized, then continue the selected increment's stack. Use a draft for unfinished or unverified work, and state what remains.
- In every PR description, include the increment number and name, the checkbox(s) it advances or completes, a short explanation of what changed and why, dependency links, and verification results. Make the stack order obvious. Keep this text concise.
- Apply review fixes to the branch that owns the change, then update dependent branches and rerun affected checks. Keep PR bases and dependency links correct as earlier PRs merge, without duplicating their changes in later diffs.
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

Use the GitHub bot helper configured in Project-specific settings for GitHub
publishing and bot commits. Read its configured README.md before first use.

Invoke it with python3. Always pass the configured repository and the actual
absolute checkout path before the subcommand:

```text
python3 <helper-path> --repo <OWNER/REPO> --checkout <ABSOLUTE_PATH> <subcommand>
```

If the helper is unavailable or unconfigured, report the publishing blocker;
do not fall back to personal GitHub credentials.

Commands:
- check: verify authentication and repository access.
- commit --message-file PATH: commit already-staged changes as the bot.
- push --branch BRANCH: push the named branch.
- create-pr --head BRANCH --title TITLE --body-file PATH:
  create a draft PR; add --base PARENT_BRANCH for stacked PRs.
- comments --pr NUMBER: read PR comments and reviews.
- reply --pr NUMBER --body-file PATH: post a conversation comment.
- reply --pr NUMBER --review-comment-id ID --body-file PATH:
  reply in an inline review thread.

Use this helper instead of personal GitHub credentials.
Never print private keys or tokens.

Keep PRs small and focused. Base dependent PRs on their predecessor’s
branch so each diff contains only its own increment.
Run relevant checks and include validation in PR descriptions.

Do not merge PRs or push directly to the default branch.
Only push, create PRs, or post replies when authorized by the user’s task.
