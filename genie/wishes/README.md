# 🧞 Automagik-Omni Genie Wishes Context System

## 📋 Purpose

This directory contains **persistent context files** for all agent tasks and wishes. Every agent task MUST have a corresponding wish file that serves as the **shared knowledge base** for that specific objective.

## 🎯 Context Engineering Rules

### 1. **Wish File Creation**
- Every agent task gets a wish file: `genie/wishes/[task-name].md`
- Reference in agent prompts: `@genie/wishes/[task-name].md`
- Contains: objective, context, progress, discoveries, issues

### 2. **Agent Context Sharing**
- Agents MUST read their wish file before starting work
- Agents MUST update their wish file with discoveries/progress
- Agents create sub-files for detailed findings: `[task-name]/[discovery].md`

### 3. **Persistent Knowledge**
- All agent discoveries persist in wish files
- Context carries forward between agent sessions
- No knowledge lost between task handoffs

## 📁 Current Wishes

### Active Tasks
- **[unified-multichannel-endpoints.md](./unified-multichannel-endpoints.md)** - Unified API endpoints for WhatsApp and Discord channels

## 📋 Wish Template Structure

Each wish document contains:

- **🎯 Task Overview** - Clear description and goals
- **📋 Desired Outcomes** - Specific deliverables 
- **🏗️ Technical Architecture** - Implementation approach
- **🔌 API Integration References** - External API documentation
- **📁 File Structure** - Code organization plan
- **🧪 Success Criteria & Validation** - Testing strategy and acceptance criteria
- **📈 Implementation Phases** - Step-by-step development plan
- **🚀 Definition of Done** - Completion checklist

## 🎯 How to Use

1. **Review Wish**: Understand requirements and architecture
2. **Plan Implementation**: Follow the phase-based approach
3. **Track Progress**: Use success criteria as checkpoints
4. **Validate Results**: Run comprehensive test suite
5. **Mark Complete**: Ensure definition of done is met

## 🧞 Genie Philosophy

Every wish is crafted with:
- **Clear Success Metrics** 📊
- **Comprehensive Testing Strategy** 🧪
- **Detailed API References** 📚
- **Step-by-Step Implementation** 🚀
- **Performance Benchmarks** ⚡

*Your development wishes are our command!* ✨