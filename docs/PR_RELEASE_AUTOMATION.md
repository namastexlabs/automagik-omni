# 🚀 PR Release Automation Guide

## Overview

The Automagik Omni PR Release system provides automated version bumping, AI-generated PR descriptions, and an interactive feedback loop for refining release notes. This system streamlines the release process from development to production.

## 🎯 Key Features

1. **Automatic Version Bumping** - Semantic versioning based on PR labels
2. **AI-Generated Descriptions** - Claude-powered PR descriptions with project context
3. **Interactive Refinement** - `@automagik-genie` feedback system for description improvements
4. **Commit Analysis** - Intelligent change detection and categorization

## 🏷️ Release Labels

Add one of these labels to your PR from `dev` to `main` to trigger the automation:

| Label | Version Change | Example | Use Case |
|-------|---------------|---------|----------|
| `release:major` | X.0.0 | 1.2.3 → 2.0.0 | Breaking changes, major rewrites |
| `release:minor` | 0.X.0 | 1.2.3 → 1.3.0 | New features, non-breaking additions |
| `release:patch` | 0.0.X | 1.2.3 → 1.2.4 | Bug fixes, small improvements |
| `release:auto` | Auto-detect | Based on commits | Analyzes commit messages |

### Auto-Detection Logic

When using `release:auto`, the system analyzes commit messages:
- Contains `BREAKING CHANGE` or `breaking:` → **major**
- Contains `feat:` → **minor**
- Default (fixes, chores, etc.) → **patch**

## 🔄 Workflow

### 1. Create Release PR

```bash
# From dev branch with all changes ready
git checkout dev
git push origin dev

# Create PR via GitHub UI or CLI
gh pr create --base main --head dev --title "Release v0.X.0" --label "release:minor"
```

### 2. Automatic Processing

When the PR is created or labeled, the system will:

1. **Detect the version type** from the label
2. **Calculate new version** based on current version in `pyproject.toml`
3. **Bump the version** and commit to the PR branch
4. **Analyze changes** between dev and main
5. **Generate PR description** using Claude
6. **Post a comment** with instructions for refinement

### 3. Refine Description (Optional)

If you want to adjust the generated description, simply comment on the PR:

```markdown
@automagik-genie please add more details about the database migration steps
```

```markdown
@automagik-genie emphasize the performance improvements and include benchmarks
```

```markdown
@automagik-genie make the breaking changes section more prominent
```

The system will:
1. Read your feedback
2. Get the current PR context
3. Regenerate the description incorporating your suggestions
4. Update the PR description
5. Confirm the changes with a comment

## 📝 Generated Description Format

The AI generates structured PR descriptions with:

```markdown
# 🚀 Release v0.X.0

## 📋 Summary
Brief overview of the release goals and achievements

## ✨ What's New
- New features and capabilities
- Major additions to the system

## 🐛 Bug Fixes
- Issues resolved
- Problems corrected

## 🔧 Improvements
- Performance enhancements
- Code quality improvements
- Refactoring efforts

## 🏗️ Technical Changes
- Infrastructure updates
- CI/CD improvements
- Dependency updates

## 📊 Impact Analysis
- **Breaking Changes**: Yes/No with details
- **Database Migrations**: Required/Not Required
- **Configuration Changes**: Required/Not Required
- **Dependencies Updated**: List of updates

## ✅ Testing
- [ ] All tests passing
- [ ] Manual testing completed
- [ ] Performance impact assessed
- [ ] Security review completed

## 📦 Deployment Notes
Special considerations for deployment

## 🔗 Related Issues
Closes: #123, #456
Related: #789
```

## 🛠️ Manual Version Management

### Using Make Commands

```bash
# Show current version
make version

# Bump versions
make bump-patch  # 0.1.0 → 0.1.1
make bump-minor  # 0.1.0 → 0.2.0
make bump-major  # 0.1.0 → 1.0.0

# Advanced bumping with script
make version-bump TYPE=auto  # Auto-detect from commits
make version-bump TYPE=patch # Specific bump type
```

### Using Python Script

```bash
# Show current version
python scripts/bump-version.py --current

# Bump versions
python scripts/bump-version.py patch
python scripts/bump-version.py minor
python scripts/bump-version.py major
python scripts/bump-version.py auto  # Auto-detect

# Set specific version
python scripts/bump-version.py --set 2.0.0

# Dry run (preview changes)
python scripts/bump-version.py patch --dry-run
```

## 🔐 Permissions

The `@automagik-genie` feedback feature requires:
- Repository collaborator status
- Write permissions to the repository

External contributors can request changes through regular PR comments, and maintainers can use `@automagik-genie` to incorporate their feedback.

## 🎯 Best Practices

### Commit Messages

Use conventional commits for better auto-detection:

```bash
# Features (triggers minor bump)
git commit -m "feat: add multi-tenant support"
git commit -m "feat(api): implement webhook retry logic"

# Fixes (triggers patch bump)
git commit -m "fix: resolve database connection leak"
git commit -m "fix(auth): correct JWT validation"

# Breaking changes (triggers major bump)
git commit -m "feat!: redesign API response format"
git commit -m "fix: update auth flow

BREAKING CHANGE: API tokens now require scope parameter"
```

### PR Labels

- Add labels early in the PR lifecycle
- Use `release:auto` when unsure about version bump
- Combine with other labels for categorization:
  - `enhancement`
  - `bug`
  - `documentation`
  - `dependencies`

### Feedback Guidelines

When using `@automagik-genie` for refinement:

1. **Be specific** about what to add or change
2. **Reference sections** that need updates
3. **Provide context** for technical details
4. **Request examples** when needed

Good examples:
- `@automagik-genie add migration steps for the new database schema`
- `@automagik-genie include performance metrics comparing before/after`
- `@automagik-genie emphasize the security improvements in the auth system`

## 🚦 Workflow Status Checks

The PR will show status checks for:

- ✅ **Version Bump** - Version successfully updated
- ✅ **Description Generated** - AI description created
- ✅ **Tests Passing** - All CI tests succeed
- ✅ **Ready to Merge** - All checks passed

## 🔧 Configuration

### GitHub Secrets Required

```yaml
GITHUB_TOKEN: Automatically provided by GitHub Actions
ANTHROPIC_API_KEY: Claude API key for AI generation
```

### Workflow Files

- `.github/workflows/pr-auto-release.yml` - Main release workflow
- `.github/workflows/genie-pr-feedback.yml` - Feedback handler
- `scripts/bump-version.py` - Version management script

## 📚 Examples

### Example 1: Minor Release with Features

```bash
# Create PR with new features
gh pr create --base main --head dev \
  --title "Release: Add webhook retry and monitoring" \
  --label "release:minor"

# System bumps version: 0.3.1 → 0.4.0
# Generates comprehensive description
# Posts success comment
```

### Example 2: Patch Release with Fixes

```bash
# Create PR with bug fixes
gh pr create --base main --head dev \
  --title "Fix: Resolve connection issues" \
  --label "release:patch"

# System bumps version: 0.3.1 → 0.3.2
# Focuses description on fixes
```

### Example 3: Auto-Detected Major Release

```bash
# PR contains breaking changes in commits
gh pr create --base main --head dev \
  --title "Redesign API architecture" \
  --label "release:auto"

# System detects BREAKING CHANGE in commits
# Bumps version: 0.3.1 → 1.0.0
# Highlights breaking changes prominently
```

## 🆘 Troubleshooting

### Version Bump Not Triggering

- Ensure PR is from `dev` or `develop` to `main`
- Check that appropriate label is applied
- Verify GitHub Actions are enabled

### Description Not Generating

- Check `ANTHROPIC_API_KEY` secret is set
- Review workflow logs for errors
- Ensure PR has sufficient changes to analyze

### @automagik-genie Not Responding

- Verify you have write permissions
- Check the exact format: `@automagik-genie` (case-sensitive)
- Ensure comment is on a PR, not an issue

## 🔗 Related Documentation

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

*🧞 Powered by Automagik Genie - Making releases magical!*