# Agent workflow

A pinned submodule containing reusable instructions, templates, a validator, and
the GitHub bot helper. Complete one user-selected increment as small, ready,
stacked PRs, then stop for review. Each checkbox may span several PRs.

## Layout

```text
templates/AGENTS.md          Shared rules and project settings
templates/PROJECT_SPEC.md    Product requirements
templates/WORK_PLAN.md       Agreed increments and verification
scripts/check_agents.py     Guard against unintended instruction changes
github_bot/github_bot.py     Bot-only GitHub CLI
github_bot/README.md         Helper setup, commands, and limitations
github_bot/config.example.json  Placeholder configuration only
```

## Adopt as a submodule

Use `.agent-workflow` as the submodule path. The project keeps its own configured
root AGENTS.md; all helper code, reference templates, and validation come from the
pinned submodule commit. Do not edit settings inside the submodule.

1. **Bootstrap commit.** Choose a reviewed upstream commit containing the templates
   and helper. Add this repository as `.agent-workflow`, check out that commit, and
   copy its AGENTS.md template to the parent root without overwriting existing work.
   Commit `.gitmodules`, the submodule pointer, and the untouched root AGENTS.md.
   The agent needs explicit authorization for this bootstrap-only setup-gate bypass;
   `Setup confirmed` remains `no`.
2. **Settings commit.** The agent asks you to fill and approve the marked settings.
   Set the parent repository, reviewers, commands, agent prefix, source revision,
   and external bot config path. The integration branch is `master`. Paths to the
   helper, README, template, and validator already point into `.agent-workflow`.
   After your explicit confirmation, record `Setup confirmed: yes`, validate, and
   commit only the settings changes.
3. **Specification and plan.** Keep existing documents. Otherwise copy the spec
   template and write it together, then create/refine WORK_PLAN.md together. Publish
   the agreed plan as a small documentation PR when authorized.
4. **Implementation.** You select an increment and authorize its PR stack. The agent
   completes all its checkboxes as small PRs, without waiting between them for
   review or merge, then stops after verifying the selected increment.

The commits above belong on setup branches and can be small dependent PRs. Do not
push directly to master. If existing AGENTS.md has custom rules, discuss and review
how to reconcile them before replacing anything.

### Initial human setup

The helper cannot initialize or clone its own missing submodule. A human can use
these standard Git operations once, from the parent checkout after inspecting its
working tree (replace APPROVED_SHA with the reviewed commit):

```sh
git submodule add https://github.com/mongilyov/agents.md.git .agent-workflow
git -C .agent-workflow checkout --detach APPROVED_SHA
cp .agent-workflow/templates/AGENTS.md AGENTS.md
```

Run the copy only when root AGENTS.md does not already exist. New clones also need
human `git submodule update --init --recursive` before the bundled helper is
available. Agents must report unsupported bootstrap operations rather than bypass
bot-only GitHub access. After initialization, use the helper for bot commits,
pushes, fetches, and all GitHub API operations.

Configure credentials outside both repositories, following `github_bot/README.md`.
The checked-in example contains no real IDs, private key, or token. Invoke:

```text
python3 .agent-workflow/github_bot/github_bot.py \
  --config /absolute/external/path/config.json \
  --repo OWNER/REPO --checkout /absolute/path/to/parent-project <command>
```

The config is external and must be supplied explicitly. The checkout argument is
the parent project (or its worktree), not the helper's submodule directory.

## Synchronizing versus upgrading

**Synchronizing** means getting the version already recorded by the parent project.
A human's `git pull --ff-only --recurse-submodules` can fast-forward the parent and
update populated submodules to its recorded commits. It does not adopt the newest
workflow master simply because that upstream branch moved. It may fail on dirty
or diverged work; never use force/reset to hide that situation.

For agents, keep synchronization explicit and use helper-authenticated fetches.
Do not automatically pull, merge, or run `submodule update --remote` at startup.
After an authorized parent fast-forward, an initialized clean submodule can be
synchronized locally with:

```sh
git submodule update --no-fetch --checkout -- .agent-workflow
```

If the recorded commit is missing locally, fetch through the helper selecting
`--repo mongilyov/agents.md --checkout /absolute/path/to/.agent-workflow` first.
The app must have access to both repositories. Initial cloning remains human setup.

**Upgrading** means deliberately selecting a newer reviewed workflow commit:

1. Obtain user authorization and review the upstream diff, including helper code
   that will run with credentials. Fetch through the current trusted helper.
2. In a clean submodule, check out the approved commit in detached mode.
3. Refresh the root AGENTS.md shared text, preserving project settings. Update its
   recorded source revision; discuss and fill any new settings explicitly.
4. Run the bundled tests and validator. Commit the new submodule pointer and root
   AGENTS.md together in a dedicated parent-project PR.
5. If an authorized feature depends on this upgrade, place the upgrade PR at the
   bottom of its stack; base the feature's first PR on that branch. Otherwise keep
   the upgrade independent. Do not bundle the upgrade into a feature diff.

The parent commit records the submodule SHA, not edits inside it. Shared helper or
rule changes require their own upstream commit/PR first. After upstream review and
merge, a parent project may adopt that commit. No feature branches or settings
edits inside the project's submodule; use a separate upstream checkout for that work.

## Validate and protect instructions

After approved setup and before publishing:

```sh
python3 .agent-workflow/scripts/check_agents.py \
  --template .agent-workflow/templates/AGENTS.md --agents AGENTS.md
```

During bootstrap only, add `--allow-unconfigured` to check unchanged shared text.
The validator rejects edits outside settings, removed/added fields, placeholders,
and missing confirmation. It cannot prove that a human approved the settings.

Use required CI and human code-owner review for AGENTS.md, `.gitmodules`, the
submodule pointer, and the CI check itself. Protect the upstream repository too.
Instructions and submodules are not access controls, and cannot provide a 100%
guarantee against an agent with write access. These protections must be configured
in each project; this repository does not silently configure them for you.

## Stacked PRs and review

Dependent PRs target their predecessor's branch. Once the complete intended set
exists, register it with `stack --prs ...` in bottom-to-top order and verify native
GitHub stack membership. Independent PRs stay independent. The current helper
refuses changing an existing stack's membership; report that limitation rather
than pretending an extension succeeded or bypassing the helper.

Create PRs with `--ready`, request configured reviewers separately, and re-request
review once after each verified feedback batch. Notification delivery is controlled
by GitHub; never claim delivery after an error or blindly retry ambiguous writes.

```text
Increment: 01 — Connection setup
Checkboxes: advances 01.1 / completes 01.2
What: <specific change>
Why: <reason>
Stack: <parent PR or master; related PRs>
Validation: <actual checks and results; pending checks>
```

## Maintain this repository

The template is not active instructions for maintaining this repository itself.
Keep its setup placeholders. Run:

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s github_bot -v
python3 scripts/check_agents.py --template templates/AGENTS.md \
  --agents templates/AGENTS.md --allow-unconfigured
```

Never commit a real config.json, private key, token, or __pycache__. Git history and
PRs replace a changelog. Previously installed local helper copies do not update
automatically; adopted projects should use the bundled version through their pin.

[Git submodules](https://git-scm.com/docs/git-submodule) ·
[Git pull](https://git-scm.com/docs/git-pull) ·
[GitHub review requests](https://docs.github.com/en/rest/pulls/review-requests)
