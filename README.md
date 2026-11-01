# Agent workflow

Shared engineering rules and a GitHub bot helper, pinned together as a submodule.
Each project keeps a short root AGENTS.md with its own settings and an explicit
instruction to read `.agent-workflow/AGENTS.md`. Shared rules are not copied.

```text
AGENTS.md                   Shared rules: TDD, increments, small stacked PRs
templates/AGENTS.md         Project settings and link to the shared rules
templates/PROJECT_SPEC.md   Product requirements template
templates/WORK_PLAN.md      Increment and verification template
github_bot/                 Bot-only CLI, documentation, and tests
```

## New project

1. Create the repository and its initial `master` commit. Give the bot installation
   access to both the project and this workflow repository.
2. On a setup branch, add `.agent-workflow` at an approved, reviewed commit. The
   initial submodule installation is human setup because the bundled helper is not
   yet available. From the project root:

   ```sh
   git submodule add https://github.com/mongilyov/agents.md.git .agent-workflow
   git -C .agent-workflow checkout --detach APPROVED_SHA
   cp .agent-workflow/templates/AGENTS.md AGENTS.md
   ```

   Copy only if no root AGENTS.md exists. Commit the submodule pointer, .gitmodules,
   and settings template as the bootstrap commit. An agent preparing this commit
   needs an explicit setup-gate bypass limited to bootstrap.
3. Fill the root AGENTS.md together with the user. Obtain explicit approval before
   setting `Setup confirmed: yes`; commit approved settings separately. Supply the
   App and installation IDs, repository, reviewers, commands, and conventions.
   Keep the key outside the repository and pass its path through
   `GITHUB_APP_PRIVATE_KEY_PATH`. No config.json is needed.
4. Write PROJECT_SPEC.md and WORK_PLAN.md together, using the templates if needed.
   Select one increment and authorize its stack of small, ready PRs. The agent
   completes that increment across its checkboxes, then stops for review.

Publish setup changes as small PRs; never push directly to master. The Markdown
link is not automatic inclusion: the project template explicitly tells agents to
open and follow the shared file. If it is missing, initialization comes first.

## Existing project

Adopt the workflow in a dedicated migration PR from the integration branch.
Compare the old AGENTS.md with the shared rules and agree how to preserve useful
project conventions in root settings or linked project documents. Replace copied
shared text with the explicit link only after agreeing the migration. Keep existing
specifications and work plans. Do not overwrite unrelated work or automatically
rebase, retarget, or restack existing PRs.

After the migration merges, synchronize active branches when authorized so they
receive the new root instructions and submodule pin. A branch still containing the
old instructions has not adopted the new workflow yet.

For projects using the previous copied-template layout, remove obsolete source
revision/template/validator fields and any CI job invoking `check_agents.py` in
the migration PR. The comparison script and its tests have been removed; preserve
unrelated CI. The submodule pointer is the single record of the workflow version.

## Pull with submodules

Whenever pulling a project, use:

```sh
git pull --ff-only --recurse-submodules
```

Inspect the working tree first. Stop on local changes or divergence that prevent
safe synchronization; do not force or discard work. For a new clone, a human must
initialize missing submodules with `git submodule update --init --recursive`.
Recursive pull synchronizes recorded submodule commits; it does not adopt the
latest workflow master. Do not use `submodule update --remote` for routine sync.

Agents still use only the helper for GitHub access. It currently supports `fetch`,
not `pull`. The equivalent is helper-authenticated fetches for the parent and
initialized submodules, an authorized local fast-forward to the intended fetched
branch, then `git submodule update --init --recursive --no-fetch --checkout`.
Missing initialization or objects requiring unsupported network operations must be
reported for human setup. Do not invent a helper command or use personal credentials.

## Upgrade with a dedicated PR

When authorized to bump the workflow:

1. Review upstream changes and choose a reviewed commit. Fetch through the current
   trusted helper, selecting the workflow repository and submodule checkout.
2. Check out the chosen commit detached in the clean `.agent-workflow` submodule.
3. Read the updated shared rules and verify helper changes before using credentials.
   Discuss any new required settings with the user.
4. Commit the submodule pointer in a dedicated project PR. Include old/new commits,
   what changed, why, and checks performed. Usually root AGENTS.md needs no edit.
   If settings or its link need changing, include those in this PR.

If a feature depends on the bump, it can be the bottom PR of that feature's stack.
Otherwise keep it independent. Shared edits require a separate upstream PR first;
never implement them inside a project's submodule. Existing projects stay pinned
until their own upgrade PR is accepted.

## Bot and reviews

Read [the helper guide](github_bot/README.md) before first use. Agents pass approved
root settings explicitly and supply only the key path through the environment:

```text
python3 .agent-workflow/github_bot/github_bot.py \
  --app-id APP_ID --installation-id INSTALLATION_ID \
  --repo OWNER/REPO --checkout /absolute/path/to/project <command>
```

Use `create-pr --ready`, then `request-review`. After each verified feedback batch,
re-request review once with `request-review --rerequest`. Dependent PRs target their
predecessors; register the complete bottom-to-top sequence with `stack --prs ...`.
The helper currently refuses changes to an existing stack's membership; report
that limitation rather than bypassing it. Never merge automatically.

Every PR briefly states its increment number/name, what changed and why,
checkboxes advanced/completed, dependencies, and validation results.

## Maintain this repository

Root AGENTS.md contains the shared workflow. Its downstream setup gate does not
apply to maintenance of this source repository. Keep project-template settings
unfilled. For helper changes, run:

```sh
python3 -m unittest discover -s github_bot -v
```

For documentation changes, review links and adoption/migration instructions.
There is no copy-validation script or duplicated workflow revision to maintain.
Never commit private keys, tokens, config.json, or __pycache__. Existing external
helpers and other projects are not modified by updates here.

[Git submodules](https://git-scm.com/docs/git-submodule) ·
[Git pull](https://git-scm.com/docs/git-pull)
