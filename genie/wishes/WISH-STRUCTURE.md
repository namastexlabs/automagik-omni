# 📚 Wish Structure & Naming Convention

## Hierarchy Levels

### Level 00: Master Wishes
- **Purpose:** Orchestrators that define scope and split work into phases
- **Naming:** `00-[topic]-master.md`
- **Scoring:** Completes when all child wishes complete
- **Example:** `00-omni-event-fabric-master.md`

### Level 01: Child Wishes (Phases)
- **Purpose:** Executable phases/features from master wish
- **Naming:** `01-[parent]--[phase].md`
- **Scoring:** Independent planning/implementation tracking
- **Example:** `01-omni-event-fabric--foundation.md`

### Level 02: Sub-Child Wishes (Optional)
- **Purpose:** Complex child wishes that need further breakdown
- **Naming:** `02-[parent]--[grandparent]--[topic].md`
- **Reserved for future use**

## Current Wish Tree

```
00-omni-event-fabric-master.md [MASTER]
├── 01-omni-event-fabric--foundation.md [Phase 1]
├── 01-omni-event-fabric--action-queue.md [Phase 2]
└── 01-omni-event-fabric--identity-lookup.md [Future Phase 3]
```

## Wish Header Template

```markdown
# 🧞 [LEVEL TYPE] Title

**Hierarchy:** [00 Master] or [01 Child of @parent]
**Status:** DRAFT | PLANNING | EXECUTING | COMPLETE
**Planning Score:** X/100
**Implementation Score:** X/100

## 🔗 Wish Relationships
- **Parent:** @genie/wishes/[parent].md
- **Siblings:** [list]
- **Dependencies:** [what must complete first]
- **Dependents:** [what waits for this]
```

## Score Propagation Rules

1. **Master Wishes:**
   - Planning Score = Average of child wish Planning Scores
   - Implementation Score = Average of child wish Implementation Scores
   - Completes when all children complete

2. **Child Wishes:**
   - Independent scoring
   - Update parent when scores change
   - Can execute in parallel unless dependencies exist

## File Naming Benefits

- **Sortable:** Files naturally sort by hierarchy and relationship
- **Discoverable:** Clear parent-child relationships in filename
- **Parseable:** Agents can understand structure from naming pattern
- **Scalable:** Supports deep nesting if needed (02, 03 levels)

## Usage Guidelines

1. **Creating New Wishes:**
   - Always link to parent in header
   - List siblings for context
   - Specify dependencies explicitly

2. **Updating Scores:**
   - Update own scores first
   - Notify parent wish of changes
   - Log changes in Status Log with evidence

3. **Completing Wishes:**
   - Ensure Death Testament created
   - Update parent completion percentage
   - Archive if no longer active