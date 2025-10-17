# Code Coverage Policy

## Overview

Automagik Omni enforces a **progressive coverage improvement policy** to ensure code quality and test coverage increases over time.

## Policy Rules

### For PRs from `dev` → `main`

Every pull request from the `dev` branch to `main` **MUST** satisfy one of the following conditions:

1. **Increase coverage by at least 1%** compared to the current `main` branch
2. **OR** achieve **≥90% code coverage** (coverage cap)

### Enforcement

- The `coverage-enforcement.yml` GitHub Actions workflow automatically validates this requirement
- PRs that don't meet the requirement will **FAIL** the CI check
- The workflow posts a detailed comment showing:
  - Current coverage on `main`
  - Coverage in the PR
  - Difference between the two
  - Progress toward the 90% cap
  - Actionable guidance if the requirement is not met

## Current Status

- **Current Coverage**: 33% (as of 2025-10-17)
- **Target Coverage**: 90%
- **Progress**: 36.7% of goal achieved
- **Remaining**: 57% to reach cap

## How to Check Coverage Locally

### Run Tests with Coverage Report

```bash
# Using UV (recommended)
uv run pytest --cov=src --cov-report=term-missing

# Using Make
make test

# With HTML report for detailed analysis
uv run pytest --cov=src --cov-report=html
# Open htmlcov/index.html in your browser
```

### View Coverage by File

```bash
uv run pytest --cov=src --cov-report=term-missing:skip-covered
```

This shows only files with missing coverage and the specific lines that need tests.

### Generate JSON Coverage Report

```bash
uv run pytest --cov=src --cov-report=json
# Creates coverage.json with detailed metrics
```

## Strategy for Increasing Coverage

### 1. Identify Low-Coverage Areas

Focus on files with the lowest coverage first for maximum impact:

```bash
# Run coverage and look for files with <50% coverage
uv run pytest --cov=src --cov-report=term | grep -E "[0-9]+%$" | sort -t% -k1 -n
```

**Current priority areas** (as of 2025-10-17):
- Discord bot manager: 18%
- Discord interaction handler: 0%
- WhatsApp client modules: 0%
- Message router: 34%
- Agent API clients: 15%
- CLI modules: 0-15%

### 2. Write Targeted Tests

For each uncovered area, write tests that:
- Test happy paths (normal operation)
- Test error conditions (exceptions, invalid inputs)
- Test edge cases (boundary conditions, empty data)
- Test integration points (how components interact)

### 3. Use Coverage Reports

After running tests:
```bash
# Open the HTML report
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html  # or xdg-open on Linux
```

The HTML report shows:
- **Red lines**: Not executed by any test
- **Green lines**: Covered by tests
- **Yellow lines**: Partially covered (e.g., missing branch)

### 4. Run Coverage Before Committing

Before pushing to `dev`:
```bash
# Check your coverage increase
uv run pytest --cov=src --cov-report=term

# Ensure tests pass
uv run pytest

# Check code quality
make lint
make format
```

## Example: Adding 1% Coverage

To add 1% coverage with our current ~11,400 statements:
- **~114 statements** need to be covered by new tests
- This typically means:
  - 5-10 new test functions for a medium-complexity module
  - OR complete coverage of 1-2 medium-sized files
  - OR integration tests covering multiple modules

## Workflow Details

### When the Workflow Runs

The `coverage-enforcement.yml` workflow triggers on:
- Pull requests from `dev` to `main`
- Types: `opened`, `synchronize`, `reopened`

### What the Workflow Does

1. **Checkout PR branch** and run full test suite with coverage
2. **Checkout main branch** and run tests to get baseline coverage
3. **Calculate difference** between PR and main coverage
4. **Check requirements**:
   - If PR coverage ≥ 90%: ✅ PASS (cap reached)
   - If coverage increase ≥ 1%: ✅ PASS
   - Otherwise: ❌ FAIL
5. **Post detailed report** as PR comment with:
   - Coverage comparison table
   - Status (PASSED/FAILED)
   - Actionable next steps if failed
   - Progress toward 90% cap

### Workflow Outputs

The workflow generates:
- ✅ **Status check** on the PR (pass/fail)
- 💬 **PR comment** with detailed coverage report
- 📊 **Coverage artifacts** for analysis

## Troubleshooting

### My PR failed coverage check but I added tests!

1. **Check the actual coverage increase**: View the workflow comment on your PR
2. **Verify tests are running**: Ensure new tests pass and are discovered by pytest
3. **Check test coverage**: Run `pytest --cov=src --cov-report=term-missing` locally
4. **Look for untested code**: Use the HTML coverage report to find gaps

### How do I know what to test?

1. **Run coverage locally** with term-missing report
2. **Focus on critical paths**: API endpoints, core business logic, integrations
3. **Check existing tests**: Look at `tests/` for patterns and examples
4. **Test behavior, not implementation**: Focus on what the code does, not how

### The workflow failed for reasons other than coverage

1. **Check test failures**: Ensure all tests pass locally
2. **Check linting**: Run `make lint` locally
3. **Check database setup**: Workflow uses SQLite; ensure migrations work
4. **View workflow logs**: Click the workflow run for detailed error messages

## Exemptions

### When can the 1% rule be waived?

The coverage requirement may be waived for:
- **Hotfixes**: Critical bug fixes that don't affect testable code
- **Documentation-only PRs**: Changes to `.md` files, comments only
- **Configuration changes**: Updates to CI/CD, Docker, env files
- **Refactoring**: Code improvements that don't change behavior (must maintain coverage)

To request an exemption:
1. Add `[skip-coverage]` to your PR title
2. Explain in the PR description why coverage increase is not applicable
3. A maintainer will review and may override the check

**Note**: Exemptions should be rare. When in doubt, add tests.

## Best Practices

### ✅ Do This

- **Test new code**: Every new feature should include tests
- **Test bug fixes**: Add a test that reproduces the bug, then fix it
- **Integration tests**: Test how components work together
- **Focus on quality**: Meaningful tests > coverage percentage
- **Run locally first**: Check coverage before pushing

### ❌ Avoid This

- **Gaming the system**: Writing tests that don't actually verify behavior
- **Testing trivia**: Don't test framework code or trivial getters/setters
- **Ignoring failures**: Fix failing tests, don't skip them
- **Assuming coverage**: Always verify locally before pushing

## Resources

### Documentation
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest documentation](https://docs.pytest.org/)
- [Testing best practices](https://docs.python-guide.org/writing/tests/)

### Internal Resources
- Test examples: `tests/` directory
- Test configuration: `pytest.ini`
- Coverage workflow: `.github/workflows/coverage-enforcement.yml`
- Regular test workflow: `.github/workflows/pr-tests.yml`

## Questions?

If you have questions about the coverage policy:
1. Check this documentation first
2. Review existing tests for examples
3. Ask in the PR comments
4. Reach out on Discord: https://discord.gg/xcW8c7fF3R

---

**Remember**: The goal is not just higher numbers, but **better tested, more reliable code**. Quality tests catch bugs, document behavior, and give confidence to refactor.
