# Wish to GitHub Issue Migration - Workflow Documentation

**Date:** 2025-10-13
**Branch:** `feat/wish-system-integration-and-normalization`
**Related Issues:** #35, #36

---

## Overview

This document describes the workflow used to migrate all local wish files to GitHub issues, ensuring no context was lost and all work is properly tracked.

---

## Step 1: Discovery & Inventory

### 1.1 Find All Wishes
```bash
find .claude/wishes genie/wishes -name "*.md" -not -name "README.md" -not -name "WISH-STRUCTURE.md" | sort
```

**Result:** Found 19 wishes across two locations:
- `.claude/wishes/` - 1 wish
- `genie/wishes/` - 18 wishes

### 1.2 List Existing GitHub Issues
```bash
gh issue list --limit 100 --state all --json number,title,state
```

**Result:** Found 7 existing issues already linked to some wishes (#22, #29-32, #35-36)

---

## Step 2: Manual Mapping & Analysis

### 2.1 Create Comprehensive Mapping

For each wish, manually documented:
- File path
- Current status (ACTIVE, COMPLETED, PENDING, UNKNOWN)
- Related GitHub issue (if exists)
- Related PR (if exists)
- Implementation evidence
- Notes for follow-up

### 2.2 Cross-Reference with PRs
```bash
gh pr list --state merged --limit 50 --json number,title,mergedAt
```

**Key Findings:**
- PR #21: Access control implementation
- PR #24: Discord QA validation
- PR #25: Discord-WhatsApp parity
- Many completed wishes lacked PR references

### 2.3 Search for Implementation Evidence

For each wish without clear PR:
1. Read wish file content
2. Checked git log for related commits
3. Searched for keywords in PR titles
4. Checked merged PRs around wish creation dates

---

## Step 3: Create Missing Issues

### 3.1 Identify Wishes Needing Issues

**Criteria for creating issues:**
- Completed work without retrospective documentation → Create closed issue
- Active work without tracking → Create open issue
- Sub-wishes with parent issue → Skip (covered by parent)
- Documentation/meta files → Skip

**Decisions:**
- ✅ Create issues for: Untracked completed work, active work
- ❌ Skip issues for: Sub-analysis docs, self-enhancement docs, sub-documents

### 3.2 Issue Creation Process

For each wish needing an issue:

1. **Read the full wish file** to extract key information
2. **Create issue body** with:
   - What's your wish? (summary)
   - Why would this be useful? (value proposition)
   - Anything else? (context, related work, wish path)
3. **Select appropriate labels**:
   - `wish:triage` - For new/unreviewed work
   - `wish:active` - For ongoing work
   - `wish:archived` - For completed work (retrospective)
   - Type labels: `type:feature`, `type:testing`, `type:docs`
4. **Create issue via CLI**:
   ```bash
   gh issue create --title "[Wish] Title" --label "labels" --body-file /tmp/issue-body.md
   ```

### 3.3 Issues Created

**Active Work:**
1. **#41** - Polish Discord-WhatsApp Parity Implementation
   - Status: Open
   - Labels: `wish:active`

2. **#42** - Fix Test Failures to Achieve 100% Success Rate
   - Status: Open
   - Labels: `wish:active`, `type:testing`

**Retrospective (Completed Work):**
3. **#43** - Cross-Channel User Sync & API Optimization
4. **#44** - Unified Multi-Channel Endpoints
5. **#45** - Discord Parity QA Validation
6. **#46** - Discord-WhatsApp Parity Implementation
7. **#47** - Makefile Quality Audit

All retrospective issues labeled: `wish:archived`, relevant type labels

---

## Step 4: Link PRs to Issues

### 4.1 Add PR References to Retrospective Issues

For completed work with merged PRs:

```bash
gh issue comment <issue-number> --body "✅ **Completed via PR #XX**
<summary of work>
Related PRs: ...
Wish: path/to/wish.md"
```

**Links Established:**
- Issue #45 ← PR #24 (Discord QA)
- Issue #46 ← PR #25 (Discord parity)
- Issue #22 ← PR #21 (Access control)

### 4.2 Close Retrospective Issues

Since retrospective issues document completed work:

```bash
for issue in 43 44 45 46 47; do
  gh issue close $issue --comment "Closing retrospective issue. Work was completed and merged."
done
```

---

## Step 5: Make Issues Self-Documenting

### 5.1 Problem Identified

If we delete wish files, active issues (#41, #42) would lose their implementation context.

### 5.2 Solution: Add Full Context to Issues

For each active issue:

1. **Read complete wish file** (all sections)
2. **Extract key information**:
   - Executive summary
   - Success criteria
   - Implementation tasks with code examples
   - File locations
   - Test commands
   - Protection boundaries (never do)
   - Known issues and solutions
3. **Create comprehensive comment** with all context
4. **Add to issue**:
   ```bash
   gh issue comment <issue> --body-file /tmp/full-context.md
   ```

### 5.3 Update Labels

Changed issue #41 from `wish:triage` to `wish:active` since it's ready for work:

```bash
gh issue edit 41 --remove-label "wish:triage" --add-label "wish:active"
```

---

## Step 6: Clean Up Local Files

### 6.1 Verify All Context Migrated

Before deletion, verified:
- ✅ All 19 wishes mapped to issues or documented as sub-docs
- ✅ Active issues have full implementation context
- ✅ Retrospective issues have PR links
- ✅ No work will be lost

### 6.2 Delete Wish Files & Reports

```bash
# Remove entire genie folder (wishes + reports + evidence)
rm -rf genie/

# Remove .claude/wishes folder
rm -rf .claude/wishes/
```

**Files Deleted:** 44 files, 4,372 lines removed

---

## Final State

### GitHub Issues (14 wishes tracked)

**Open Issues (2):**
- #41 - Polish Discord-WhatsApp Parity (wish:active)
- #42 - Fix Test Failures (wish:active, 99.2% complete)

**Closed Issues (5):**
- #43 - Cross-Channel User Sync (wish:archived)
- #44 - Unified Multi-Channel Endpoints (wish:archived)
- #45 - Discord Parity QA (wish:archived, PR #24)
- #46 - Discord-WhatsApp Parity (wish:archived, PR #25)
- #47 - Makefile Quality Audit (wish:archived)

**Existing Issues (7):**
- #22 - Multi-Channel Access Control (enhancement, PR #21)
- #29-32 - Event Fabric Foundation phases (planned-feature)
- #35 - Wish system integration (current work)
- #36 - Review and normalize wishes (current work)

### Wishes Without Issues (5)

Intentionally excluded (don't need GitHub tracking):
- Sub-wish analysis documents (covered by parent #42)
- Makefile audit sub-documents (covered by parent #47)
- Self-enhancement documentation

---

## Lessons Learned

### What Worked Well

1. **Manual mapping first** - Understanding all wishes before creating issues prevented duplicates
2. **Retrospective issues** - Documenting completed work provides valuable history
3. **Full context in issues** - Makes issues self-contained and wish files deletable
4. **CLI-based workflow** - Fast iteration with `gh` commands

### Process Improvements

1. **Earlier GitHub adoption** - Create issues as wishes are created
2. **PR-to-issue linking** - Link PRs to issues immediately upon merge
3. **Consistent labeling** - Use `wish:*` labels from the start
4. **Status updates** - Update wish status when PRs merge

### Key Patterns Established

1. **Wish → Issue** - Every wish gets an issue (unless sub-document)
2. **Retrospective closure** - Completed wishes become closed issues with PR links
3. **Active self-documentation** - Open issues contain full implementation context
4. **Clean workspace** - Delete local files after migration

---

## Commands Reference

### Discovery
```bash
# Find wishes
find .claude/wishes genie/wishes -name "*.md" | sort

# List issues
gh issue list --limit 100 --state all

# List merged PRs
gh pr list --state merged --limit 50
```

### Issue Management
```bash
# Create issue
gh issue create --title "[Wish] Title" --label "labels" --body-file file.md

# Add comment
gh issue comment <number> --body "comment text"
gh issue comment <number> --body-file file.md

# Edit labels
gh issue edit <number> --add-label "label"
gh issue edit <number> --remove-label "label"

# Close issue
gh issue close <number> --comment "reason"
```

### Cleanup
```bash
# Stage deletions
git add -A

# Commit
git commit -m "commit message"
```

---

## Outcome

✅ **100% of wishes tracked in GitHub**
✅ **0 context lost** - All implementation details preserved
✅ **Clean repository** - 44 files removed, 4,372 lines deleted
✅ **Self-documenting issues** - Active issues contain full context
✅ **Historical record** - Retrospective issues document completed work

**Migration complete!** All future work tracked in GitHub issues from the start.
