# Git Hooks for Automagik Omni

This directory contains git hooks to maintain code quality and prevent common issues.

## 🚀 Quick Setup

Run the setup script to configure the hooks:

```bash
./.githooks/setup.sh
```

Or manually:

```bash
chmod +x .githooks/pre-commit .githooks/pre-push
git config core.hooksPath .githooks
```

## 📋 Available Hooks

### Pre-commit Hook
Runs before each commit to ensure code quality:
- ✅ **Linting** - Checks for code style issues with ruff
- ✅ **Formatting** - Ensures consistent code formatting
- ✅ **Security** - Scans for API keys and sensitive data
- ✅ **File Size** - Prevents large files (>5MB) from being committed
- ⚠️ **Type Checking** - Warns about type issues (non-blocking)

### Pre-push Hook
Runs before pushing to remote:
- ✅ **Tests** - Ensures all tests pass
- ✅ **Final Lint** - Double-checks code quality
- ⚠️ **TODOs** - Warns about TODO/FIXME comments
- ⚠️ **Commit Messages** - Checks for conventional commit format
- ⚠️ **Protected Branches** - Warns when pushing to main/master

## 🔧 Manual Commands

If hooks fail, use these commands to fix issues:

```bash
# Fix linting issues
make lint-fix

# Fix formatting
make format

# Run tests
make test

# Run all checks
make lint && make test
```

## 🚨 Bypassing Hooks

In emergency situations, you can bypass hooks (use sparingly):

```bash
# Skip pre-commit hook
git commit --no-verify -m "Emergency fix"

# Skip pre-push hook
git push --no-verify
```

## 📝 Conventional Commits

We recommend using conventional commit format:

```
feat: add new feature
fix: resolve bug
docs: update documentation
style: formatting changes
refactor: code restructuring
test: add tests
chore: maintenance tasks
build: build system changes
ci: CI/CD changes
perf: performance improvements
```

## 🔍 Hook Customization

Edit the hook files directly to customize checks:
- `.githooks/pre-commit` - Modify commit-time checks
- `.githooks/pre-push` - Modify push-time checks

## 🐛 Troubleshooting

If hooks aren't running:
1. Ensure hooks are executable: `chmod +x .githooks/*`
2. Check git configuration: `git config core.hooksPath`
3. Verify you're in the right directory
4. Try running the setup script again

## 🤝 Contributing

When adding new checks to hooks:
1. Test thoroughly before committing
2. Document any new requirements
3. Keep checks fast to avoid slowing down development
4. Make checks helpful with clear error messages