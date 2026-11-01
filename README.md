# Agent workflow

Reusable templates for TDD, small stacked PRs, and implementing one selected
increment at a time. Each increment may contain several checkboxes, and each
checkbox may span several PRs. Review happens after the increment's stack is ready;
merging remains under human control.

## Templates

- `templates/AGENTS.md`: shared engineering rules and a project-specific settings section.
- `templates/PROJECT_SPEC.md`: intended product, boundaries, and acceptance criteria.
- `templates/WORK_PLAN.md`: collaboratively agreed increments, outcomes, and verification.

## Adopt in a project

1. Copy `templates/AGENTS.md` to the project's root. If an AGENTS.md already exists,
   merge the relevant rules carefully instead of overwriting it.
2. Fill in its Project-specific settings using the real repository, integration
   branch, reviewers, commands, architecture references, and bot helper paths. Checkout paths
   are resolved at runtime, so worktrees use their own paths. Keep credentials out.
3. Keep the project's existing PROJECT_SPEC.md. For a new project, copy its template
   and write the specification together before implementation.
4. Discuss the existing WORK_PLAN.md with the agent, or create it together from the
   template. Record the agreed plan in a small documentation PR when authorized.
5. Explicitly select an increment and state whether publishing its PRs is authorized.
   The agent implements and verifies the whole increment as small stacked PRs,
   then stops for review before starting another increment.

Example task:

> Implement Increment 01: Connection setup from the agreed WORK_PLAN.md.
> Create its small stacked PRs ready for review using the configured bot helper.
> Request review from mongilyov on every PR.
> Complete and verify the whole increment, then stop for review. Do not merge.

## PR description

Keep each description short, using this structure:

```text
Increment: 01 — Connection setup
Checkboxes: advances 01.1 / completes 01.2
What: <specific change in this PR>
Why: <reason this change is needed>
Stack: <parent PR or integration branch; related PR links>
Validation: <checks actually run and their results; pending checks>
```

A checkbox is marked `[x]` in the PR that completes and verifies it, including
its dependencies. The default branch receives that checkmark only after merge.

## Maintain the shared workflow

Commit template changes here, then adopt them through small PRs in each project.
Preserve each project's settings and intentional exceptions. Record the source
commit in a comment in adopted AGENTS.md files when useful, for example:

```markdown
<!-- Shared workflow source: <repository URL>, commit <SHA> -->
```

Use real committed copies rather than live symlinks or instructions to fetch the
latest rules at runtime: each project should adopt changes explicitly. Git history
and PR descriptions are sufficient for this small repository; no changelog is needed.

The templates are starter documents, not instructions for maintaining this template
repository itself. Do not copy placeholder settings into active project instructions.
