---
name: commit-message
description: Generate one concise Conventional Commits message from staged repository changes when explicitly invoked as `$commit-message`.
---

# Commit Message

When explicitly invoked as `$commit-message`:

1. Inspect only staged changes in the current repository. Ignore unstaged and
   untracked changes.
2. Identify the primary purpose of the changes without inventing work that is
   not present.
3. Return one concise commit message using Conventional Commits.

Use an optional scope only when it adds useful context. Follow any language or
format preference included alongside the invocation.

Return only the proposed commit message in a code block. Do not modify files,
stage changes, or create the commit unless the user explicitly requests those
actions separately.

If there are no staged changes, state that there are no staged changes instead
of inventing a commit message.
