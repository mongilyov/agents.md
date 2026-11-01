# Agent workflow

Reusable templates for TDD and small stacked PRs. Implement an entire selected
increment, including all its checkboxes, then stop for review. A checkbox may span
several PRs. Each verified PR is ready for review and requests the configured human
reviewers. After verified review fixes, re-request review once per feedback batch.

## Files

- `templates/AGENTS.md`: setup gate, project settings, and shared workflow rules.
- `templates/PROJECT_SPEC.md`: product requirements and acceptance criteria.
- `templates/WORK_PLAN.md`: jointly agreed increments, outcomes, and verification.
- `scripts/check_agents.py`: detect edits outside the settings section and incomplete setup.
- `tests/`: offline tests for the validator.

## Recommended adoption: pinned copies

Use committed copies, updated through explicit PRs. This keeps projects independent
of local paths, network availability, and submodule initialization.

1. Choose an approved commit of this repository. Copy `templates/AGENTS.md` to the
   project's root; merge existing instructions deliberately instead of overwriting.
   If deliberate project-specific shared rules differ, establish and review that
   customized baseline explicitly before using the validator.
2. Copy the unmodified selected template to `.agent-workflow/AGENTS.template.md`
   and its validator to `.agent-workflow/check_agents.py` in the project.
3. The agent must explicitly ask you to complete and approve project settings before
   any other work. It may inspect other files to propose settings only with your
   permission. Fill only the marked section. Confirm setup explicitly, then record
   `Setup confirmed: yes`. Only an explicit user instruction can bypass this gate.
4. Set integration branch to `master`; choose the actual agent prefix and reviewers.
   Set the repository, commands, architecture references, helper paths, and source
   commit. Set pinned template and validator paths to the files above. Never store
   credentials in these documents.
5. Keep an existing PROJECT_SPEC.md, or write one together using the template.
   Discuss an existing WORK_PLAN.md, or create it together. Record the agreed plan
   in a small documentation PR when publishing is authorized.
6. Select an increment and authorize publishing its stack. Do not wait for review
   after every checkbox; stop when the selected increment is implemented and verified.

After setup, and before publishing, run from the project root:

```sh
python3 .agent-workflow/check_agents.py \
  --template .agent-workflow/AGENTS.template.md --agents AGENTS.md
```

During setup only, `--allow-unconfigured` checks that shared text is unchanged.
It does not approve settings or authorize feature work. The validator checks text
and a recorded confirmation; it cannot prove the human actually approved it.

## Protecting the workflow

The validator fails if any text outside the marked settings section differs from
the pinned baseline. It also rejects unfilled settings or missing confirmation.
Run it in CI and require a human review for AGENTS.md, `.agent-workflow/`, and the
CI check itself. Configure CODEOWNERS and branch protection/rulesets where available.
These protections are an adoption step; this repository does not configure them
in your projects automatically. Prompts, copies, and submodules alone cannot
provide a 100% guarantee against an agent changing files it can write.

For an explicitly requested workflow update, review the upstream diff, then update
the pinned template, validator, recorded source revision, and shared AGENTS.md
text in one dedicated PR. Preserve project settings. Do not update automatically
from GitHub during feature work. Git history and PRs replace a changelog.

## If you prefer a submodule

A submodule stores a particular upstream commit in the parent repository. It does
not automatically load instructions for agents, protect files from edits, or copy
settings into the parent project. Keep a real, configured root AGENTS.md.

You may pin this repository at `.agent-workflow/source` instead of storing baseline
copies. Point the project settings and validator command to:

```text
Pinned template: .agent-workflow/source/templates/AGENTS.md
Validator: .agent-workflow/source/scripts/check_agents.py
```

Initialize the submodule at the parent-recorded commit when cloning. Treat its
contents as read-only during project work. Do not fill project settings there or
make feature branches inside it. No automatic `submodule update --remote`.

For an authorized update, select a reviewed upstream commit, check it out in the
submodule, refresh the root AGENTS.md shared text while retaining settings, validate,
and commit the new submodule pointer plus root AGENTS.md in a parent-project PR.
Other clones get the new version only after receiving that parent commit and
updating their submodules. Local edits inside a submodule are not captured by a
parent commit: upstream changes need their own commit, push, and upstream PR first.

For this small workflow, pinned copies are the simpler default. A submodule is an
optional way to store the pinned source, not a separate instructions lifecycle.

## Bot-only GitHub operations

Use only the configured `github_bot.py` CLI. No helper imports, ad-hoc API scripts,
GitHub CLI, curl, or personal credentials. Its installed README defines supported
commands; if a command is missing, report the blocker rather than bypassing it.
The helper itself is installed separately and is not bundled in this repository.

Pass `--repo OWNER/REPO --checkout ABSOLUTE_PATH` before every subcommand.
The current workflow requires check, fetch, commit, push, create-pr --ready, ready,
pr, checks, comments, reply, request-review (including --rerequest), and stack.
Run check to inspect grants. Checks:read and Actions:read are needed for private CI
inspection in addition to Contents:write, Pull requests:write, Metadata:read, and
Statuses:read. Editing workflow files may need Workflows:write as well.

Example after completing and pushing review fixes:

```text
python3 <helper> --repo <OWNER/REPO> --checkout <PATH> request-review \
  --pr <NUMBER> --reviewers <LOGIN> --rerequest
```

GitHub documents that re-requests trigger notifications. Delivery to a device or
email inbox depends on GitHub and reviewer preferences; verify the API accepted
it without claiming notification delivery. Do not re-notify after every commit
or retry a request whose response was lost automatically.

## PR description

```text
Increment: 01 — Connection setup
Checkboxes: advances 01.1 / completes 01.2
What: <specific change in this PR>
Why: <reason this change is needed>
Stack: <parent PR or master; related PR links>
Validation: <checks actually run and their results; pending checks>
```

## Maintain this repository

The template is not active instructions for maintaining this repository itself.
Keep placeholders in the template. Validate changes with:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_agents.py --template templates/AGENTS.md \
  --agents templates/AGENTS.md --allow-unconfigured
```

## References

- [Git submodule behavior](https://git-scm.com/docs/git-submodule)
- [GitHub review requests and re-requests](https://docs.github.com/en/rest/pulls/review-requests)
