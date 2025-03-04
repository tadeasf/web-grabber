#!/usr/bin/env python3
"""
Script to set up pre-commit hooks for the project.
"""

import subprocess
import sys
from pathlib import Path


def check_git_repo():
    """Check if we're in a git repository."""
    if not Path(".git").exists():
        print(
            "Error: No .git directory found. Are you in the root of the git repository?"
        )
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
            subprocess.run(["pip", "install", "pre-commit"], check=True)
            print("pre-commit successfully installed.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing pre-commit: {e}")
            return False


def install_hooks():
    """Install the pre-commit hooks."""
    try:
        subprocess.run(["pre-commit", "install"], check=True)
        print("Pre-commit hooks installed successfully.")

        # Configure Git to automatically stage fix changes
        try:
            subprocess.run(
                ["git", "config", "--local", "pre-commit.autostage", "true"], check=True
            )
            print("Configured pre-commit to auto-stage fixes.")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not configure auto-staging: {e}")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing pre-commit hooks: {e}")
        return False


def verify_hook_config():
    """Verify that the pre-commit config file exists."""
    config_path = Path(".pre-commit-config.yaml")
    if not config_path.exists():
        print(f"Error: {config_path} not found.")
        return False
    print("Found pre-commit configuration file.")
    return True


def test_version_bump():
    """Test that the version bump script works."""
    try:
        # Check if the script exists
        bump_script = Path("scripts/bump_version.py")
        if not bump_script.exists():
            print(f"Error: {bump_script} not found.")
            return False

        # Make the script executable
        bump_script.chmod(0o755)

        print("Testing version bump script...")
        # Run the script with dry-run option
        result = subprocess.run(
            [sys.executable, str(bump_script), "--dry-run"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        print(result.stdout)
        print("Version bump script test successful.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error testing version bump script: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    """Main function to set up pre-commit hooks."""
    print("Setting up pre-commit hooks...")

    if not check_git_repo():
        return 1

    if not install_pre_commit():
        return 1

    if not verify_hook_config():
        return 1

    if not install_hooks():
        return 1

    if not test_version_bump():
        print("Warning: Version bump script test failed, but continuing...")

    print("All done! Pre-commit hooks are set up and ready to use.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
