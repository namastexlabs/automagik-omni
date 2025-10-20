# GitHub Actions Workflow Optimization Proposal

## Current Problem

Tests are being run **3-4 times** on a single push to dev:

1. **Pre-push hook**: Full test suite (~72s)
2. **pr-tests.yml**: Full test suite with coverage (~72s)
3. **coverage-enforcement.yml**: Tests run TWICE (~144s total)
   - Once on PR branch (dev)
   - Once on main branch for comparison
4. **test-suite.yml**: Additional test run (if triggered)

**Total redundant time: ~288-360 seconds (5-6 minutes) of duplicate testing**

## Proposed Streamlined Approach

### Option 1: Smart Caching (Recommended)
Use test results from `pr-tests.yml` in `coverage-enforcement.yml`

```yaml
# coverage-enforcement.yml (OPTIMIZED)
jobs:
  enforce-coverage-increase:
    needs: [] # Remove this - run independently
    steps:
      - name: Download PR coverage from pr-tests workflow
        uses: dawidd6/action-download-artifact@v3
        with:
          workflow: pr-tests.yml
          name: test-results-3.12
          path: ./pr-coverage/

      - name: Use cached PR coverage
        run: |
          PR_COVERAGE=$(python -c "import json; data=json.load(open('pr-coverage/coverage.json')); print(data['totals']['percent_covered'])")
          echo "PR_COVERAGE=$PR_COVERAGE" >> $GITHUB_OUTPUT

      # Only run tests on main branch for comparison
      - name: Checkout main and run tests
        # ... (keep existing main branch test)
```

**Benefits:**
- Eliminates 1 full test run (~72s saved)
- Still validates coverage requirements
- Reuses work already done

### Option 2: Combine Workflows
Merge `coverage-enforcement.yml` into `pr-tests.yml` as a conditional job

```yaml
# pr-tests.yml (ENHANCED)
jobs:
  test:
    # ... existing test job

  enforce-coverage:
    name: Enforce Coverage (dev→main only)
    needs: test
    if: github.event.pull_request.base.ref == 'main' && github.event.pull_request.head.ref == 'dev'
    runs-on: ubuntu-latest
    steps:
      - name: Get PR coverage from previous job
        run: |
          # Use artifacts from test job
          PR_COVERAGE=${{ needs.test.outputs.coverage }}

      - name: Checkout main and compare
        # ... run tests only on main branch
```

**Benefits:**
- Single workflow file to maintain
- Natural dependency chain
- Clearer logic flow

### Option 3: Conditional Test Execution (Most Aggressive)
Only run full tests when code changes, use cached results otherwise

```yaml
# pr-tests.yml (SMART CACHING)
jobs:
  check-changes:
    runs-on: ubuntu-latest
    outputs:
      should_test: ${{ steps.filter.outputs.src }}
    steps:
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            src:
              - 'src/**'
              - 'tests/**'
              - 'pyproject.toml'

  test:
    needs: check-changes
    if: needs.check-changes.outputs.should_test == 'true'
    # ... existing test job

  use-cached:
    needs: check-changes
    if: needs.check-changes.outputs.should_test == 'false'
    runs-on: ubuntu-latest
    steps:
      - name: Use previous test results
        run: echo "No code changes, using cached results"
```

**Benefits:**
- Skip tests entirely for docs-only changes
- Fastest for non-code PRs
- Most complex to implement

## Recommended Implementation

**Phase 1: Quick Win (Option 1)**
- Implement artifact sharing between workflows
- **Time saved: ~72s per PR (20% reduction)**
- **Effort: 1-2 hours**

**Phase 2: Consolidation (Option 2)**
- Merge coverage enforcement into pr-tests
- **Time saved: ~144s per PR (40% reduction)**
- **Effort: 2-3 hours**

**Phase 3: Smart Caching (Option 3)**
- Add conditional execution
- **Time saved: up to 288s for doc changes (80% reduction)**
- **Effort: 3-4 hours**

## Additional Optimizations

### 1. Remove Pre-push Hook Test Duplication
Since GitHub Actions runs tests anyway:

```bash
# .githooks/pre-push (SIMPLIFIED)
#!/bin/bash
# Run ONLY fast checks (lint, format)
# Let CI handle full test suite

echo "🔍 Running pre-commit checks..."
make lint
make format --check

echo "✅ Pre-push checks passed!"
echo "⏳ Full test suite will run in GitHub Actions"
```

**Time saved: 72s locally per push**

### 2. Parallel Test Execution
Use pytest-xdist for faster tests:

```yaml
- name: Run tests with coverage
  run: |
    pytest tests/ \
      -n auto \  # Run in parallel
      --cov=src \
      --cov-report=json
```

**Time saved: ~30-40s (tests complete in ~35-40s instead of ~72s)**

### 3. Coverage-Only on dev→main
Regular PRs don't need coverage enforcement:

```yaml
# pr-tests.yml
- name: Run tests (fast mode)
  if: github.base_ref != 'main'
  run: pytest tests/ --tb=short  # No coverage

- name: Run tests with coverage
  if: github.base_ref == 'main'
  run: pytest tests/ --cov=src  # With coverage
```

**Time saved: ~5-10s per PR to dev**

## Implementation Priority

| Optimization | Time Saved | Effort | Priority |
|--------------|-----------|---------|---------|
| Remove pre-push tests | 72s local | Low | **HIGH** |
| Artifact caching (Option 1) | 72s CI | Medium | **HIGH** |
| Parallel execution | 35s CI | Low | **HIGH** |
| Workflow consolidation | 144s CI | Medium | **MEDIUM** |
| Smart caching | 288s CI | High | **LOW** |

## Total Potential Savings

**Current: ~360s (6 minutes) of testing per push**
**Optimized: ~100s (1.7 minutes) of testing per push**

**Result: 70% reduction in CI time** 🚀

---

## Next Steps

1. Review this proposal
2. Choose optimization approach
3. Implement Phase 1 (artifact caching)
4. Measure improvements
5. Iterate based on results
