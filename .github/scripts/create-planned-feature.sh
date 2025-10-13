#!/bin/bash
# .github/scripts/create-planned-feature.sh
# Creates a planned feature issue from JSON input

set -e

# Show usage
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
  cat << 'EOF'
Usage: cat issue.json | ./.github/scripts/create-planned-feature.sh

JSON Format (see planned-feature-issue-template.json):
{
  "title": "Issue title",
  "initiative": "39",
  "description": "What needs to be done",
  "acceptance_criteria": ["criterion 1", "criterion 2"],
  "context": "Optional context",
  "dependencies": {
    "blocked_by": ["#123"],
    "blocks": ["#456"]
  },
  "work_type": "Feature Implementation",
  "complexity": "M - 3-5 days",
  "priority": "high",
  "areas": ["API", "Testing"],
  "labels": ["type:feature", "area:api"]
}

Examples:
  # Create from JSON file
  cat tempo/issues/issue-1-1.json | ./.github/scripts/create-planned-feature.sh

  # Create multiple issues
  for file in tempo/issues/*.json; do
    cat "$file" | ./.github/scripts/create-planned-feature.sh
    sleep 2  # Rate limiting
  done
EOF
  exit 0
fi

# Read JSON from stdin and remove documentation fields (_comment, _help, etc)
JSON=$(cat | jq 'with_entries(select(.key | startswith("_") | not))')

# Parse fields
TITLE=$(echo "$JSON" | jq -r '.title')
INITIATIVE=$(echo "$JSON" | jq -r '.initiative')
DESCRIPTION=$(echo "$JSON" | jq -r '.description')
CONTEXT=$(echo "$JSON" | jq -r '.context // "N/A"')
WORK_TYPE=$(echo "$JSON" | jq -r '.work_type // "Feature Implementation"')
COMPLEXITY=$(echo "$JSON" | jq -r '.complexity // "M - 3-5 days"')
PRIORITY=$(echo "$JSON" | jq -r '.priority // "medium"')

# Build acceptance criteria checkboxes
ACCEPTANCE_CRITERIA=$(echo "$JSON" | jq -r '.acceptance_criteria // [] | map("- [ ] " + .) | join("\n")')

# Build dependencies section
BLOCKED_BY=$(echo "$JSON" | jq -r '.dependencies.blocked_by // [] | map("- " + .) | join("\n")')
BLOCKS=$(echo "$JSON" | jq -r '.dependencies.blocks // [] | map("- " + .) | join("\n")')

DEPENDENCIES=""
if [[ -n "$BLOCKED_BY" ]]; then
  DEPENDENCIES="**Blocked by:**\n$BLOCKED_BY"
fi
if [[ -n "$BLOCKS" ]]; then
  if [[ -n "$DEPENDENCIES" ]]; then
    DEPENDENCIES="$DEPENDENCIES\n\n"
  fi
  DEPENDENCIES="${DEPENDENCIES}**Blocks:**\n$BLOCKS"
fi
if [[ -z "$DEPENDENCIES" ]]; then
  DEPENDENCIES="N/A"
fi

# Build labels
LABELS=$(echo "$JSON" | jq -r '.labels // [] | join(",")')
if [[ -z "$LABELS" ]]; then
  LABELS="planned-feature,priority:$PRIORITY"
else
  LABELS="planned-feature,$LABELS"
fi

# Build issue body
BODY=$(cat <<EOF
## 🔗 Roadmap Initiative Number

$INITIATIVE

## 📄 Description

$DESCRIPTION

## ✅ Acceptance Criteria

$ACCEPTANCE_CRITERIA

## 🔍 Context / Evidence

$CONTEXT

## 🧩 Dependencies

$DEPENDENCIES

## 📋 Metadata

**Work Type:** $WORK_TYPE
**Estimated Complexity:** $COMPLEXITY
**Priority:** $PRIORITY
EOF
)

# Create the issue
echo "Creating issue: $TITLE"
echo "Initiative: #$INITIATIVE"
echo "Labels: $LABELS"
echo ""

ISSUE_URL=$(echo "$BODY" | gh issue create \
  --repo namastexlabs/automagik-omni \
  --title "$TITLE" \
  --label "$LABELS" \
  --body-file -)

ISSUE_NUMBER=$(echo "$ISSUE_URL" | grep -oP '/issues/\K\d+')
echo "✓ Created issue #$ISSUE_NUMBER: $ISSUE_URL"

# Add comment linking to roadmap initiative
gh issue comment "$ISSUE_NUMBER" \
  --repo namastexlabs/automagik-omni \
  --body "🗺️ **Roadmap Initiative:** namastexlabs/automagik-roadmap#${INITIATIVE}" \
  > /dev/null 2>&1 || echo "  ⚠ Could not add initiative comment"

echo ""
