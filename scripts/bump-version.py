#!/usr/bin/env python3
"""
Version Bump Script for Automagik Omni

Handles semantic versioning for the project, updating pyproject.toml
and optionally creating git tags.
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Tuple, Optional


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse semantic version string into tuple of integers."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(map(int, match.groups()))


def bump_version(current: str, bump_type: str) -> str:
    """
    Bump version based on type (major, minor, patch).
    
    Args:
        current: Current version string (e.g., "1.2.3")
        bump_type: Type of bump ("major", "minor", "patch")
    
    Returns:
        New version string
    """
    major, minor, patch = parse_version(current)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def get_current_version(pyproject_path: Path) -> str:
    """Extract current version from pyproject.toml."""
    content = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def update_pyproject_version(pyproject_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml."""
    content = pyproject_path.read_text()
    updated = re.sub(
        r'^(version\s*=\s*")[^"]+(")',
        f'\\1{new_version}\\2',
        content,
        flags=re.MULTILINE
    )
    pyproject_path.write_text(updated)


def detect_bump_type_from_commits(since_ref: str = "origin/main") -> str:
    """
    Auto-detect version bump type from commit messages.
    
    Uses conventional commits to determine:
    - BREAKING CHANGE or ! -> major
    - feat: -> minor
    - fix:, chore:, etc -> patch
    """
    import subprocess
    
    try:
        # Get commit messages since the reference
        result = subprocess.run(
            ["git", "log", f"{since_ref}..HEAD", "--pretty=format:%s %b"],
            capture_output=True,
            text=True,
            check=True
        )
        
        commits = result.stdout.lower()
        
        # Check for breaking changes
        if "breaking change" in commits or "breaking:" in commits:
            return "major"
        
        # Check commit types
        if re.search(r'^feat(\(.*\))?:', commits, re.MULTILINE):
            return "minor"
        
        # Default to patch
        return "patch"
        
    except subprocess.CalledProcessError:
        # If we can't get commits, default to patch
        return "patch"


def main():
    parser = argparse.ArgumentParser(
        description="Bump version for Automagik Omni"
    )
    parser.add_argument(
        "type",
        nargs="?",
        choices=["major", "minor", "patch", "auto"],
        help="Type of version bump (or 'auto' to detect from commits)"
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Just print current version and exit"
    )
    parser.add_argument(
        "--set",
        metavar="VERSION",
        help="Set specific version (e.g., 1.2.3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    # Find pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("Error: pyproject.toml not found", file=sys.stderr)
        sys.exit(1)
    
    # Get current version
    current_version = get_current_version(pyproject_path)
    
    if args.current:
        print(current_version)
        return
    
    # Determine new version
    if args.set:
        # Validate the provided version
        try:
            parse_version(args.set)
            new_version = args.set
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.type:
        if args.type == "auto":
            bump_type = detect_bump_type_from_commits()
            print(f"Auto-detected bump type: {bump_type}")
        else:
            bump_type = args.type
        
        new_version = bump_version(current_version, bump_type)
    else:
        parser.print_help()
        sys.exit(1)
    
    print(f"Version: {current_version} → {new_version}")
    
    if not args.dry_run:
        update_pyproject_version(pyproject_path, new_version)
        print(f"✅ Updated pyproject.toml to version {new_version}")
    else:
        print("(dry run - no changes made)")


if __name__ == "__main__":
    main()