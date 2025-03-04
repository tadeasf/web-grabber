#!/usr/bin/env python3
"""
Script to set up pre-commit hooks for the project.
"""

import os
import subprocess
import sys
from pathlib import Path

def check_git_repo():
    """Check if we're in a git repository."""
    if not Path(".git").exists():
        print("Error: No .git directory found. Are you in the root of the git repository?")
        return False
    return True

def install_pre_commit():
    """Install pre-commit if not already installed."""
    try:
        subprocess.run(["pre-commit", "--version"], check=True, stdout=subprocess.PIPE)
        print("pre-commit is already installed.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing pre-commit...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pre-commit"], check=True)
            print("pre-commit installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing pre-commit: {e}")
            return False

def install_hooks():
    """Install the pre-commit hooks."""
    print("Installing pre-commit hooks...")
    try:
        subprocess.run(["pre-commit", "install"], check=True)
        print("Pre-commit hooks installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing hooks: {e}")
        return False

def verify_hook_config():
    """Verify the pre-commit config file exists."""
    config_path = Path(".pre-commit-config.yaml")
    if not config_path.exists():
        print(f"Error: {config_path} not found.")
        return False
    print("Pre-commit configuration file found.")
    return True

def test_version_bump():
    """Test the version bump hook."""
    print("\nTesting version bump hook...")
    try:
        result = subprocess.run(
            ["pre-commit", "run", "version-bump", "--all-files"], 
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if "Skipped" in result.stdout or "Failed" in result.stdout:
            print("Version bump hook test failed or was skipped.")
            print(f"Output: {result.stdout}")
            print(f"Error: {result.stderr}")
            return False
        print("Version bump hook test successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error testing hook: {e}")
        return False

def main():
    """Set up pre-commit hooks."""
    print("Setting up version bump pre-commit hook...\n")
    
    if not check_git_repo():
        sys.exit(1)
    
    if not verify_hook_config():
        sys.exit(1)
    
    if not install_pre_commit():
        sys.exit(1)
    
    if not install_hooks():
        sys.exit(1)
    
    test_version_bump()
    
    print("\nSetup completed!")
    print("Now, every time you make a commit, the minor version will automatically increase.")
    print("To manually test the hook, run: pre-commit run version-bump --all-files")

if __name__ == "__main__":
    main()