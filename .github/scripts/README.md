# GitHub Scripts

Utility scripts for development and automation.

## Git Status Scripts

### git-status-full.sh
Comprehensive git and PR status report with detailed information.

**Usage:**
```bash
./.github/scripts/git-status-full.sh
```

**Output includes:**
- Current branch and working tree status
- Recent commits (last 10)
- Pull request information (number, title, state, URL, commit count)
- Branch tracking and upstream status
- Repository statistics
- File changes summary (modified, staged, untracked)
- Stash list (if any)

### git-status-oneliner.sh
Compact version with essential information.

**Usage:**
```bash
./.github/scripts/git-status-oneliner.sh
```

**Output includes:**
- Current branch
- Working tree status
- Recent commits (last 5)
- PR info (if exists)
- Upstream tracking
- Basic statistics

## Feature Planning

### create-planned-feature.sh
Create GitHub issues from planned feature template.

**Usage:**
```bash
./.github/scripts/create-planned-feature.sh
```

## Requirements

- Git
- GitHub CLI (`gh`) - for PR information
- `jq` - for JSON parsing

## Quick Access

Add to your shell profile for quick access from anywhere:

```bash
# ~/.bashrc or ~/.zshrc
alias gitstatus='cd /path/to/automagik-omni && ./.github/scripts/git-status-full.sh'
alias gs-quick='cd /path/to/automagik-omni && ./.github/scripts/git-status-oneliner.sh'
```
