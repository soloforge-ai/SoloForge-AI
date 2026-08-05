# SoloForge AI Rules

Version: v1.0.0

---

# Purpose

This document defines the engineering standards and operational rules for all AI assistants working on the SoloForge AI project.

Its purpose is to ensure consistency, maintainability, and predictable development behavior regardless of which AI model is used.

These rules apply to every coding, documentation, architecture, and development task.

---

# Core Principles

Every AI assistant must follow these principles.

## 1. Consistency First

Maintain consistency with the existing architecture.

Do not introduce a different coding style or architecture unless explicitly requested.

---

## 2. Minimal Changes

Only modify the files necessary to complete the requested task.

Avoid touching unrelated code.

---

## 3. Preserve Stability

Never sacrifice project stability for unnecessary optimization.

Working code is more valuable than clever code.

---

## 4. Explain Important Decisions

Whenever a design decision affects the project structure, architecture, or future maintenance, explain the reasoning.

---

## 5. Human Collaboration

The AI is an engineering assistant.

Final architectural decisions always belong to the project owner.

---

# Project Structure Rules

Always preserve the current project structure.

Do not rename or move folders without approval.

Current structure includes:

- frontend/
- backend/
- assets/
- data/
- docs/
- tools/
- prompts/
- rules/
- .ai/

New folders should only be created when they provide clear long-term architectural value.

---

# Coding Standards

## General

Write clean and maintainable code.

Prefer readability over clever implementations.

Keep functions focused on a single responsibility.

Avoid duplicated logic.

Avoid unnecessary abstractions.

---

## File Modification

Modify only the requested files.

If more than three files need modification:

- stop
- explain why
- request confirmation

Never rewrite the project unless explicitly requested.

---

## Refactoring

Refactor only when it improves:

- readability
- maintainability
- scalability

Never refactor unrelated modules.

---

## Error Handling

Never ignore errors.

Handle exceptions gracefully.

Prefer meaningful error messages.

Avoid silent failures.

---

## Performance

Optimize only after correctness.

Avoid premature optimization.

---

# Flutter Rules

Follow Material 3.

Preserve the existing theme.

Keep widgets modular.

Prefer reusable widgets.

Avoid unnecessary widget nesting.

Separate UI from business logic whenever possible.

---

# Documentation Rules

Human documentation belongs in:

docs/

AI documentation belongs in:

.ai/

Do not duplicate information across documents.

Documentation should be updated only when project behavior changes.

---

# Git Rules

Use Conventional Commits.

Examples

feat(frontend):

feat(scanner):

feat(forge):

fix(frontend):

docs(protocol):

refactor(frontend):

test(scanner):

chore(build):

Commit messages should be concise and descriptive.

---

# AI Behavior Rules

Always understand the task before writing code.

Never invent project architecture.

Never assume missing project information.

If information is missing:

ask first.

Never fabricate APIs.

Never fabricate project files.

Never fabricate database structures.

---

# Communication Rules

Be concise.

Be technically accurate.

Explain complex decisions clearly.

Avoid unnecessary explanations.

If uncertain:

state the uncertainty.

Do not guess.

---

# Output Rules

When returning code:

1. List modified files.

2. Explain what changed.

3. Explain why.

4. Return complete code.

Never return partial implementations unless explicitly requested.

Avoid placeholder implementations.

Avoid pseudo-code unless requested.

---

# Architecture Rules

Respect existing architecture.

Do not replace working architecture without approval.

Prefer extending existing systems instead of rebuilding them.

Favor modular design.

Favor scalable solutions.

Avoid introducing unnecessary dependencies.

---

# Documentation Update Policy

Whenever project behavior changes:

Update only the affected documentation.

Avoid editing unrelated documents.

Documentation should always remain synchronized with the codebase.

---

# Definition of Done

A task is considered complete only when:

✓ Requested functionality works.

✓ Existing functionality remains intact.

✓ No unrelated files were modified.

✓ Documentation is updated if required.

✓ Code is readable.

✓ Architecture remains consistent.

✓ Changes are explained.

---

# Never Do

Never:

- Rename folders without approval.
- Delete project files without approval.
- Rewrite unrelated modules.
- Replace architecture unnecessarily.
- Introduce breaking changes without warning.
- Ignore project conventions.
- Invent missing project information.
- Hide errors.
- Return incomplete implementations.

---

# Always Do

Always:

- Read AI_CONTEXT.md first.
- Follow AI_TASK.md.
- Follow this document.
- Preserve project consistency.
- Minimize changes.
- Explain architectural decisions.
- Produce maintainable code.
- Think long-term.

---

End of Document