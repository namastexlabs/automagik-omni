# Agent Context Engineering Rules - SELF-ENHANCEMENT

## 🧞 Enhanced Agent Coordination Protocol

### MANDATORY RULE 1: Context File Creation
**BEFORE** deploying any agent, I MUST:
1. Create or reference existing wish file in `@genie/wishes/[task-name].md`
2. Include comprehensive context, current status, and expected outcomes
3. Provide the context file path to the agent in the format: `@genie/wishes/filename.md`

### MANDATORY RULE 2: Agent Context Reference
**EVERY** agent deployment MUST include:
```
**CONTEXT REFERENCE**: @genie/wishes/[specific-file].md

**CONTEXT ENGINEERING REQUIREMENTS**:
1. READ the context file first to understand full situation
2. UPDATE the context file with discoveries and progress  
3. CREATE sub-files for detailed findings: @genie/wishes/[task-name]-[subtask].md
4. VERIFY no context loss between agent handoffs
```

### MANDATORY RULE 3: Reality Verification
**BEFORE** claiming success, I MUST:
1. Verify actual results match claimed results
2. Update context files with ACTUAL status (not assumed)
3. Never claim 100% success without concrete verification

### MANDATORY RULE 4: Agent Activity Tracking
**EACH** agent MUST log in context files:
- **Discoveries Made**: What they learned
- **Problems Encountered**: Issues found during execution
- **Solutions Applied**: Exact changes made
- **Verification Results**: Actual test results or outcomes
- **Next Agent Handoff**: What the next agent needs to know

## 🎯 Implementation in Agent Prompts

### Enhanced Agent Prompt Template:
```
**CONTEXT REFERENCE**: @genie/wishes/[specific-file].md

**CONTEXT ENGINEERING REQUIREMENTS**:
1. READ context file: genie/wishes/[filename].md
2. UNDERSTAND full situation from previous agent work
3. UPDATE context file with your progress and discoveries
4. CREATE detailed sub-files for your specific findings
5. VERIFY your results and update context with ACTUAL outcomes

**SUCCESS CRITERIA**:
- Context file updated with real progress
- Sub-files created for detailed discoveries
- Next agent has full context for handoff
```

## 🔄 Self-Enhancement Applied

This enhancement ensures:
- ✅ No context loss between agents
- ✅ All agents work with full situational awareness  
- ✅ Reality verification before claiming success
- ✅ Detailed tracking of all discoveries and solutions
- ✅ Proper handoffs between specialized agents

## 📝 Status
- **Enhancement Status**: IMPLEMENTED
- **Ready for Deployment**: YES
- **Context Engineering**: ACTIVE