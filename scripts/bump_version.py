#!/usr/bin/env python3
"""
Pre-commit hook to automatically bump the minor version number
in both pyproject.toml and __init__.py.
"""

import re
import sys
import subprocess
from pathlib import Path

# File paths
PYPROJECT_PATH = Path("pyproject.toml").absolute()
INIT_PATH = Path("src/web_grabber/__init__.py").absolute()

def bump_version_in_pyproject():
    """Update the version in pyproject.toml."""
    if not PYPROJECT_PATH.exists():
        print(f"Error: {PYPROJECT_PATH} not found.")
        return False
    
    content = PYPROJECT_PATH.read_text()
    
    # Find current version
    version_pattern = re.compile(r'version\s*=\s*"(\d+)\.(\d+)\.(\d+)"')
    match = version_pattern.search(content)
    
    if not match:
        print("Error: Could not find version string in pyproject.toml")
        return False
    
    major, minor, patch = map(int, match.groups())
    new_minor = minor + 1
    new_version = f'{major}.{new_minor}.{patch}'
    
    # Replace version
    new_content = version_pattern.sub(f'version = "{new_version}"', content)
    PYPROJECT_PATH.write_text(new_content)
    
    print(f"Bumped version in pyproject.toml: {major}.{minor}.{patch} -> {new_version}")
    return new_version

def bump_version_in_init(new_version):
    """Update the version in __init__.py."""
    if not INIT_PATH.exists():
        print(f"Error: {INIT_PATH} not found.")
        return False
    
    content = INIT_PATH.read_text()
    
    # Find current version
    version_pattern = re.compile(r'__version__\s*=\s*"([^"]+)"')
    match = version_pattern.search(content)
    
    if not match:
        print("Error: Could not find __version__ in __init__.py")
        return False
    
    # Replace version
    new_content = version_pattern.sub(f'__version__ = "{new_version}"', content)
    INIT_PATH.write_text(new_content)
    
    print(f"Updated version in __init__.py to: {new_version}")
    return True

def stage_files():
    """Stage the modified version files."""
    try:
        # Print the full paths for debugging
        print(f"Staging files: {PYPROJECT_PATH} and {INIT_PATH}")
        
        # Stage the modified files
        subprocess.run(["git", "add", str(PYPROJECT_PATH), str(INIT_PATH)], check=True)
        print("Staged modified version files.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error staging files: {e}")
        return False

def check_file_exists():
    """Check if version files exist."""
    pyproject_exists = PYPROJECT_PATH.exists()
    init_exists = INIT_PATH.exists()
    
    if not pyproject_exists:
        print(f"Error: pyproject.toml not found at {PYPROJECT_PATH}")
    
    if not init_exists:
        print(f"Error: __init__.py not found at {INIT_PATH}")
    
    return pyproject_exists and init_exists

def main():
    """Main function."""
    print("Running version bump pre-commit hook...")
    
    if not check_file_exists():
        sys.exit(1)
    
    new_version = bump_version_in_pyproject()
    if not new_version:
        sys.exit(1)
    
    if not bump_version_in_init(new_version):
        sys.exit(1)
    
    if not stage_files():
        print("Warning: Could not stage files. Please add them manually.")
    
    print("Version bump completed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()