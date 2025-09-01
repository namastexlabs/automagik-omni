#!/bin/bash
# Setup script for git hooks

echo "🔧 Setting up git hooks..."

# Make hooks executable
chmod +x .githooks/pre-commit
chmod +x .githooks/pre-push

# Configure git to use the hooks
git config core.hooksPath .githooks

echo "✅ Git hooks configured successfully!"
echo ""
echo "The following hooks are now active:"
echo "  • pre-commit: Runs linting, formatting, and security checks"
echo "  • pre-push: Runs tests and comprehensive checks before push"
echo ""
echo "To bypass hooks in emergency (use sparingly):"
echo "  git commit --no-verify"
echo "  git push --no-verify"