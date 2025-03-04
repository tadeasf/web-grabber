# Git Workflow Guide

This document provides guidance on working with the project's Git workflow, particularly regarding pre-commit hooks.

## Pre-commit Hooks

This project uses pre-commit hooks to automate:
- Version bumping (patch version increased with each commit)
- Code linting with `ruff`
- Code formatting with `ruff formatter`

## Common Issues and Solutions

### Issue: Commit Fails Due to Linting/Formatting Changes

If your commit fails with messages like:
```
Fixing errors automatically...
Found 8 errors (8 fixed, 0 remaining)...
15 files reformatted, 7 files left unchanged...
Stashed changes conflicted with hook auto-fixes...
```

This happens because the pre-commit hooks are modifying your files, but those changes aren't staged yet.

#### Solutions:

1. **Option 1: Run Pre-commit Manually First (Recommended)**
   ```bash
   pre-commit run --all-files
   git add -A
   git commit -m "Your commit message"
   ```

2. **Option 2: Use the Automatic Staging**
   We've configured Git to automatically stage changes made by hooks. Simply restart your terminal to ensure the configuration takes effect, then try committing again.

3. **Option 3: Two-Step Commit Process**
   ```bash
   git commit -m "Your commit message"  # This will likely fail but fix files
   git add -A
   git commit -m "Your commit message"  # This should now succeed
   ```

## Setting Up Pre-commit Hooks

If you're new to the project or haven't set up the hooks yet:

```bash
python scripts/setup_hooks.py
```

This will:
- Install pre-commit if needed
- Configure the hooks
- Set up auto-staging of fixes
- Test the version bump script

## Updating the Hooks

If changes are made to the `.pre-commit-config.yaml` file, you should run:

```bash
pre-commit clean
pre-commit install
```

to ensure the new configuration is active.

## Bypassing Hooks (Emergency Only)

In rare cases where you need to bypass the hooks (NOT RECOMMENDED):

```bash
git commit -m "Your commit message" --no-verify
```

Always try to fix the actual issues instead of bypassing the hooks.