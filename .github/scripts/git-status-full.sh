#!/bin/bash
# Comprehensive git status report - one-liner expanded for readability

set -euo pipefail

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                          GIT & PR STATUS REPORT                                ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Current branch info
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 CURRENT BRANCH: $CURRENT_BRANCH"
echo ""

# Git status
echo "📊 WORKING TREE STATUS:"
git status --short --branch
echo ""

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo "⚠️  UNCOMMITTED CHANGES DETECTED"
else
    echo "✅ CLEAN WORKING TREE"
fi
echo ""

# Recent commits
echo "📝 RECENT COMMITS (last 10):"
git log --oneline --graph --decorate -10
echo ""

# PR information (if gh CLI is available)
if command -v gh &> /dev/null; then
    echo "🔗 PULL REQUEST INFO:"
    PR_JSON=$(gh pr list --head "$CURRENT_BRANCH" --json number,title,state,url,isDraft,baseRefName,headRefName 2>/dev/null || echo "[]")

    if [[ "$PR_JSON" != "[]" && "$PR_JSON" != "" ]]; then
        PR_NUMBER=$(echo "$PR_JSON" | jq -r '.[0].number // "N/A"')
        PR_TITLE=$(echo "$PR_JSON" | jq -r '.[0].title // "N/A"')
        PR_STATE=$(echo "$PR_JSON" | jq -r '.[0].state // "N/A"')
        PR_URL=$(echo "$PR_JSON" | jq -r '.[0].url // "N/A"')
        PR_DRAFT=$(echo "$PR_JSON" | jq -r '.[0].isDraft // false')
        PR_BASE=$(echo "$PR_JSON" | jq -r '.[0].baseRefName // "N/A"')

        echo "  PR #$PR_NUMBER: $PR_TITLE"
        echo "  State: $PR_STATE $([ "$PR_DRAFT" = "true" ] && echo "(DRAFT)" || echo "")"
        echo "  Base: $PR_BASE → Head: $CURRENT_BRANCH"
        echo "  URL: $PR_URL"

        # Get commit count
        COMMIT_COUNT=$(gh pr view "$PR_NUMBER" --json commits --jq '.commits | length' 2>/dev/null || echo "N/A")
        echo "  Commits: $COMMIT_COUNT"

    else
        echo "  ℹ️  No PR found for branch: $CURRENT_BRANCH"
    fi
else
    echo "🔗 PULL REQUEST INFO: (gh CLI not available)"
fi
echo ""

# Branch tracking info
echo "🌿 BRANCH TRACKING:"
git branch -vv | grep "^\*"
echo ""

# Upstream comparison
UPSTREAM_BRANCH=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "")
if [[ -n "$UPSTREAM_BRANCH" ]]; then
    AHEAD=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo "0")
    BEHIND=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "0")
    echo "🔄 UPSTREAM STATUS ($UPSTREAM_BRANCH):"
    echo "  Behind: $AHEAD commits"
    echo "  Ahead: $BEHIND commits"
else
    echo "🔄 UPSTREAM STATUS: No tracking branch"
fi
echo ""

# Statistics
echo "📈 STATISTICS:"
TOTAL_COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo "0")
CONTRIBUTORS=$(git shortlog -sn --all | wc -l)
LAST_COMMIT_DATE=$(git log -1 --format=%cd --date=relative)
echo "  Total commits (this branch): $TOTAL_COMMITS"
echo "  Contributors: $CONTRIBUTORS"
echo "  Last commit: $LAST_COMMIT_DATE"
echo ""

# Modified files summary
MODIFIED_COUNT=$(git diff --name-only | wc -l)
STAGED_COUNT=$(git diff --cached --name-only | wc -l)
UNTRACKED_COUNT=$(git ls-files --others --exclude-standard | wc -l)

echo "📂 FILE CHANGES:"
echo "  Modified: $MODIFIED_COUNT"
echo "  Staged: $STAGED_COUNT"
echo "  Untracked: $UNTRACKED_COUNT"
echo ""

# Show stashes if any
STASH_COUNT=$(git stash list | wc -l)
if [[ $STASH_COUNT -gt 0 ]]; then
    echo "💾 STASHES: $STASH_COUNT"
    git stash list | head -5
    echo ""
fi

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                              END OF REPORT                                     ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
