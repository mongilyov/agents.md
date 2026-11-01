# Work plan: <Project name>

Based on PROJECT_SPEC.md. Discuss and agree on this plan before implementation.
The presence of an increment does not authorize starting it; the user explicitly
selects an increment. Complete that increment as small stacked PRs, then stop for
review. Do not pause between its checkboxes merely to await review or merge.

Checkboxes represent outcomes, not PRs. One checkbox may span multiple PRs.
Mark it complete only in the PR that finishes and verifies the outcome; record
contributing PRs when available. Unfinished or unverified outcomes stay unchecked.

## Increment 01: <Feature name>

Purpose: <User-visible result and why it matters.>

Dependencies: <Earlier increments or prerequisites, or None.>

Scope: <Included behavior and explicit exclusions.>

- [ ] 01.1 <Outcome>. Depends on: <None or IDs>. Verify: <specific check>.
- [ ] 01.2 <Outcome>. Depends on: <IDs>. Verify: <specific check>.

### Proposed PR stack

<Small changes in dependency order. Split further when needed to keep diffs small.
Each behavior change includes its tests. Several PRs may contribute to one checkbox.>

### Increment verification

<Checks proving the complete feature works across the stack.>

### PRs and evidence

<Record PR links, contributing checkbox IDs, actual checks and results, and blockers.
Do not record planned verification as completed evidence.>

## Later increments

<Add numbered, named increments together with the user as the plan develops.>
