#!/bin/bash
# tests/e2e/run_all.sh
# Master test runner for all E2E tests
#
# Usage:
#   chmod +x tests/e2e/run_all.sh
#   ./tests/e2e/run_all.sh

set -e

echo "========================================="
echo "Automagik Omni - E2E Test Suite"
echo "PostgreSQL-Native Migration"
echo "========================================="
echo ""

# Test directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Test results
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_script="$2"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    TESTS_RUN=$((TESTS_RUN + 1))

    if bash "$SCRIPT_DIR/$test_script"; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo ""
        echo "✅ $test_name: PASSED"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo ""
        echo "❌ $test_name: FAILED"
    fi
}

# Run all tests
run_test "Platform Compatibility Check" "platform_check.sh"
run_test "Fresh Installation" "fresh_install.sh"
run_test "localStorage Migration" "localstorage_migration.sh"
run_test "Backup & Restore" "backup_restore.sh"

# Print summary
echo ""
echo "========================================="
echo "Test Suite Summary"
echo "========================================="
echo ""
echo "Total tests run:    $TESTS_RUN"
echo "Tests passed:       $TESTS_PASSED"
echo "Tests failed:       $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "✅ All tests passed!"
    echo ""
    echo "Migration Status: READY FOR DEPLOYMENT"
    echo ""
    echo "Next Steps:"
    echo "  1. Commit changes: git add . && git commit -m 'PostgreSQL-native migration'"
    echo "  2. Test on actual system: make run"
    echo "  3. Run Alembic migrations: cd src && alembic upgrade head"
    echo "  4. Verify UI: http://localhost:3000"
    echo "  5. Create PR to merge to dev branch"
    exit 0
else
    echo "❌ Some tests failed"
    echo ""
    echo "Migration Status: NEEDS ATTENTION"
    echo ""
    echo "Failed Tests:"
    [ $TESTS_FAILED -gt 0 ] && echo "  - Check test output above for details"
    echo ""
    echo "Recommended Actions:"
    echo "  1. Review failed test output"
    echo "  2. Fix identified issues"
    echo "  3. Re-run: ./tests/e2e/run_all.sh"
    exit 1
fi
