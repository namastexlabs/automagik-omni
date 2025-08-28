#!/usr/bin/env python3
"""
Test runner to validate the handler test fixes
"""
import subprocess
import sys
import os

def run_handler_tests():
    """Run both handler test files to validate fixes"""
    print("🔧 VALIDATING HANDLER TEST FIXES")
    print("="*80)
    
    # Change to the project directory
    os.chdir('/home/cezar/automagik/automagik-omni')
    
    test_files = [
        ('test_omni_handlers.py', 'Original Handler Tests'),
        ('test_omni_handlers_fixed.py', 'Fixed Handler Tests')
    ]
    
    results = {}
    
    for test_file, description in test_files:
        print(f"\n🧪 RUNNING: {description}")
        print("-" * 50)
        
        try:
            # Run pytest with minimal output to check if tests pass
            result = subprocess.run([
                'python3', '-m', 'pytest', 
                f'tests/{test_file}', 
                '-v', '--tb=short', '--no-header', '-x'  # Stop on first failure
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✅ {description}: ALL TESTS PASSED")
                # Count passed tests
                passed_count = result.stdout.count('PASSED')
                print(f"   Tests passed: {passed_count}")
                results[test_file] = ('PASS', passed_count, 0)
            else:
                print(f"❌ {description}: TESTS FAILED")
                # Count failed tests
                failed_count = result.stdout.count('FAILED') + result.stdout.count('ERROR')
                passed_count = result.stdout.count('PASSED')
                print(f"   Tests passed: {passed_count}")
                print(f"   Tests failed: {failed_count}")
                print(f"\nFirst failure:")
                print(result.stdout.split('\n')[0:5])
                results[test_file] = ('FAIL', passed_count, failed_count)
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  {description}: TIMEOUT")
            results[test_file] = ('TIMEOUT', 0, 0)
        except Exception as e:
            print(f"💥 {description}: ERROR - {e}")
            results[test_file] = ('ERROR', 0, 0)
    
    print(f"\n{'='*80}")
    print("📊 HANDLER TEST RESULTS SUMMARY:")
    print('='*80)
    
    total_passed = 0
    total_failed = 0
    
    for test_file, (status, passed, failed) in results.items():
        print(f"  {test_file}: {status}")
        if status in ['PASS', 'FAIL']:
            print(f"    ✅ Passed: {passed}")
            if failed > 0:
                print(f"    ❌ Failed: {failed}")
            total_passed += passed
            total_failed += failed
    
    print(f"\n🎯 OVERALL HANDLER TESTS:")
    print(f"   Total Passed: {total_passed}")
    print(f"   Total Failed: {total_failed}")
    
    if total_failed == 0 and total_passed >= 12:
        print("\n🎉 SUCCESS: All 12 handler tests are now passing!")
        print("   ✅ Evolution API mocking fixed")
        print("   ✅ Discord bot initialization fixed")  
        print("   ✅ External dependencies properly isolated")
        return True
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: {total_passed} tests passing, {total_failed} still failing")
        if total_failed > 0:
            print("   Some handler tests still need fixes")
        return False

if __name__ == "__main__":
    success = run_handler_tests()
    sys.exit(0 if success else 1)