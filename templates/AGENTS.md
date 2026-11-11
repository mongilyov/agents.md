# Project instructions

Before any repository work, read and follow [the shared workflow](.agent-workflow/AGENTS.md).
Read that file explicitly; a Markdown link does not automatically load instructions.
Resolve its project paths from this repository root, not from the submodule.
If the file is missing, stop and ask for submodule initialization.

If setup is unconfirmed or any setting below is unfilled, ask the user to complete
and approve setup before other work. Bypass only when explicitly authorized.

## Project-specific settings

- Setup confirmed: no

Fill these in when adopting this template. Replace placeholders with verified
values; use `not applicable` where appropriate. Never store credentials here.

- Repository: `<OWNER/REPO>`
- Reviewers: `<GitHub usernames to request on every PR>`
- Integration branch: `master`
- Agent branch prefix: `<agent_name>` (for example, `codex`, `claude`, or another agent name)
- Setup command: `<command>`
- Build command: `<command or not applicable>`
- Focused test command: `<command with test selector>`
- Full test command: `<command>`
- Other required checks: `<lint, typecheck, integration checks, etc.>`
- UI verification: `<launch command and affected-flow verification, or not applicable>`
- Architecture and conventions: `<key constraints and links to repository docs>`
- Workflow submodule: `.agent-workflow`
- GitHub bot helper: `.agent-workflow/github_bot/github_bot.py`
- GitHub bot README: `.agent-workflow/github_bot/README.md`
- GitHub App ID: `<numeric app ID>`
- GitHub installation ID: `<numeric installation ID>`
- Private-key path environment variable: `GITHUB_APP_PRIVATE_KEY_PATH` (optional override; otherwise the helper reads the ignored `.github-bot-key-path` in the project root)
