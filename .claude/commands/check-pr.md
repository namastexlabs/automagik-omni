---
description: Analyze current PR status and provide comprehensive state assessment
---

You are analyzing the current pull request status and repository state. Follow these steps:

## 1. Gather PR Information

Run the git status script to get comprehensive information:

```bash
! ./.github/scripts/git-status-full.sh
```

## 2. Fetch Detailed PR Data

Get complete PR details including checks, reviews, and metadata:

```bash
! gh pr view --json number,title,state,isDraft,url,baseRefName,headRefName,commits,additions,deletions,changedFiles,reviews,statusCheckRollup,mergeable,mergeStateStatus,reviewDecision,labels,milestone,assignees,author,createdAt,updatedAt
```

## 3. Get PR Diff Summary

Fetch a summary of changes:

```bash
! gh pr diff --name-status
```

## 4. Check CI/CD Status

Get the status of checks and workflows:

```bash
! gh pr checks
```

## 5. Analyze and Report

Based on the gathered information, provide a comprehensive analysis including:

### PR Overview
- **PR Number & Title**
- **Status**: Open/Closed/Merged/Draft
- **Author & Creation Date**
- **Base Branch** → **Head Branch**
- **URL**

### Code Changes
- **Commits**: Total count and recent commits
- **Files Changed**: Count and breakdown by type
- **Lines**: Additions (+) and Deletions (-)
- **Significant Changes**: Highlight key files/areas modified

### Review Status
- **Review Decision**: Approved/Changes Requested/Pending
- **Reviewers**: Who has reviewed and their status
- **Comments**: Count of review comments
- **Requested Reviews**: Pending reviewers

### CI/CD Status
- **Checks Status**: Pass/Fail/Pending
- **Failed Checks**: List any failing checks with details
- **Required Checks**: Status of required checks for merge
- **Workflow Runs**: Recent workflow execution status

### Merge Readiness
- **Mergeable State**: Can it be merged?
- **Merge Conflicts**: Any conflicts to resolve?
- **Required Checks**: All passing?
- **Required Reviews**: Satisfied?
- **Branch Status**: Up to date with base?

### Work Status
- **Working Tree**: Clean or uncommitted changes?
- **Upstream Sync**: Ahead/behind remote?
- **Stashes**: Any stashed changes?
- **Untracked Files**: New files not committed?

### Recommendations

Provide actionable recommendations based on the analysis:

1. **Immediate Actions**: What needs to be done right now?
2. **Blockers**: What's preventing merge?
3. **Next Steps**: Suggested workflow to move forward
4. **Warnings**: Any concerns or risks?

### Summary

Provide a concise 2-3 sentence summary of:
- Where the PR is in its lifecycle
- What's been accomplished
- What remains to be done

## Output Format

Use clear formatting with:
- ✅ for completed/passing items
- ⚠️ for warnings or pending items
- ❌ for failures or blockers
- 📊 for statistics
- 🔍 for detailed findings
- 💡 for recommendations

## Additional Context

If relevant, check:
- Related issues or PRs
- Project boards or milestones
- Recent activity or discussions
- Deployment status (if applicable)

Be thorough but concise. Focus on actionable insights rather than repeating raw data.
