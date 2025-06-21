#!/usr/bin/env python3
"""
Validation script for multi-tenancy implementation.
Checks code quality, security, and production readiness.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Any


def check_file_structure() -> Dict[str, bool]:
    """Check that all required files exist for multi-tenancy."""
    required_files = {
        "Database Layer": [
            "src/db/__init__.py",
            "src/db/database.py", 
            "src/db/models.py",
            "src/db/bootstrap.py"
        ],
        "API Layer": [
            "src/api/deps.py",
            "src/api/routes/__init__.py",
            "src/api/routes/instances.py"
        ],
        "CLI Tools": [
            "src/cli/instance_cli.py"
        ],
        "Tests": [
            "tests/test_database_models.py",
            "tests/test_webhook_routing.py",
            "tests/test_crud_api.py",
            "tests/conftest.py"
        ]
    }
    
    results = {}
    print("📁 Checking file structure...")
    
    for category, files in required_files.items():
        print(f"\n{category}:")
        category_results = []
        for file_path in files:
            exists = Path(file_path).exists()
            status = "✅" if exists else "❌"
            print(f"  {status} {file_path}")
            category_results.append(exists)
        results[category] = all(category_results)
    
    return results


def check_async_patterns(file_path: Path) -> List[str]:
    """Check for proper async/await usage in FastAPI handlers."""
    if not file_path.exists():
        return [f"File not found: {file_path}"]
    
    issues = []
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check webhook handlers should be async
                if 'webhook' in node.name.lower() or 'handle' in node.name.lower():
                    if not hasattr(node, 'decorator_list') or not any(
                        isinstance(d, ast.Name) and d.id == 'async' for d in getattr(node, 'decorator_list', [])
                    ):
                        # Check if function def is actually async
                        if not isinstance(node, ast.AsyncFunctionDef):
                            issues.append(f"Function {node.name} should be async for webhook handling")
    
    except Exception as e:
        issues.append(f"Error parsing {file_path}: {e}")
    
    return issues


def check_security_patterns(file_path: Path) -> List[str]:
    """Check for security best practices."""
    if not file_path.exists():
        return [f"File not found: {file_path}"]
    
    issues = []
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for hardcoded secrets
        if 'api_key' in content.lower() and 'os.getenv' not in content and 'config.' not in content:
            if any(secret in content.lower() for secret in ['secret', 'password', 'token']) and 'test' not in str(file_path):
                issues.append("Potential hardcoded secrets found")
        
        # Check for SQL injection protection
        if 'execute(' in content and '?' not in content and 'f"' in content:
            issues.append("Potential SQL injection vulnerability - use parameterized queries")
        
        # Check for input validation
        if 'request.json()' in content and 'BaseModel' not in content:
            issues.append("Missing input validation with Pydantic models")
        
        # Check for error information disclosure
        if 'except Exception as e:' in content and 'str(e)' in content and 'HTTPException' in content:
            if 'detail=str(e)' in content:
                issues.append("Potential information disclosure in error messages")
    
    except Exception as e:
        issues.append(f"Error checking security in {file_path}: {e}")
    
    return issues


def check_error_handling(file_path: Path) -> List[str]:
    """Check for proper error handling patterns."""
    if not file_path.exists():
        return [f"File not found: {file_path}"]
    
    issues = []
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for bare except clauses
        if 'except:' in content:
            issues.append("Bare except clause found - should catch specific exceptions")
        
        # Check for logging in exception handlers
        if 'except Exception' in content and 'logger.' not in content:
            issues.append("Exception handling without logging")
        
        # Check for proper FastAPI error responses
        if 'def ' in content and 'webhook' in content and 'HTTPException' not in content:
            issues.append("Webhook handlers should use HTTPException for errors")
    
    except Exception as e:
        issues.append(f"Error checking error handling in {file_path}: {e}")
    
    return issues


def check_configuration_management() -> List[str]:
    """Check configuration management patterns."""
    issues = []
    
    config_file = Path("src/config.py")
    if config_file.exists():
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Check for Pydantic BaseModel usage
        if 'BaseModel' not in content:
            issues.append("Configuration should use Pydantic BaseModel")
        
        # Check for environment variable loading
        if 'load_dotenv' not in content:
            issues.append("Configuration should load environment variables")
        
        # Check for proper field definitions
        if 'Field(' not in content:
            issues.append("Configuration fields should use Pydantic Field")
    else:
        issues.append("Configuration file not found")
    
    return issues


def check_database_patterns() -> List[str]:
    """Check database implementation patterns."""
    issues = []
    
    # Check models file
    models_file = Path("src/db/models.py")
    if models_file.exists():
        with open(models_file, 'r') as f:
            content = f.read()
        
        # Check for SQLAlchemy 2.0 patterns
        if 'declarative_base' in content and 'DeclarativeBase' not in content:
            issues.append("Consider using SQLAlchemy 2.0 DeclarativeBase pattern")
        
        # Check for proper constraints
        if 'unique=True' not in content:
            issues.append("Missing unique constraints in database models")
        
        # Check for proper indexing
        if 'index=True' not in content:
            issues.append("Missing database indexes for performance")
    else:
        issues.append("Database models file not found")
    
    return issues


def check_api_patterns() -> List[str]:
    """Check FastAPI implementation patterns."""
    issues = []
    
    # Check main app file
    app_file = Path("src/api/app.py")
    if app_file.exists():
        with open(app_file, 'r') as f:
            content = f.read()
        
        # Check for CORS configuration
        if 'CORSMiddleware' not in content:
            issues.append("CORS middleware not configured")
        
        # Check for dependency injection
        if 'Depends(' not in content:
            issues.append("Missing dependency injection patterns")
        
        # Check for proper status codes
        if 'status_code=' not in content:
            issues.append("Missing explicit status codes in responses")
        
        # Check for request validation
        if '@app.post' in content and 'Request' in content and 'BaseModel' not in content:
            issues.append("Missing request validation with Pydantic models")
    else:
        issues.append("FastAPI app file not found")
    
    return issues


def main():
    """Run all validation checks."""
    print("🔍 Multi-Tenancy Implementation Validation")
    print("=" * 50)
    
    all_issues = []
    
    # File structure check
    structure_results = check_file_structure()
    if not all(structure_results.values()):
        all_issues.append("Missing required files")
    
    # Code quality checks
    print("\n🔧 Code Quality Checks...")
    key_files = [
        Path("src/api/app.py"),
        Path("src/api/routes/instances.py"),
        Path("src/db/models.py"),
        Path("src/cli/instance_cli.py")
    ]
    
    for file_path in key_files:
        if file_path.exists():
            print(f"\nChecking {file_path}:")
            
            # Async patterns
            async_issues = check_async_patterns(file_path)
            if async_issues:
                print(f"  ⚠️  Async issues: {len(async_issues)}")
                all_issues.extend(async_issues)
            else:
                print("  ✅ Async patterns OK")
            
            # Security
            security_issues = check_security_patterns(file_path)
            if security_issues:
                print(f"  ❌ Security issues: {len(security_issues)}")
                all_issues.extend(security_issues)
            else:
                print("  ✅ Security patterns OK")
            
            # Error handling
            error_issues = check_error_handling(file_path)
            if error_issues:
                print(f"  ⚠️  Error handling issues: {len(error_issues)}")
                all_issues.extend(error_issues)
            else:
                print("  ✅ Error handling OK")
    
    # Configuration management
    print("\n⚙️  Configuration Management...")
    config_issues = check_configuration_management()
    if config_issues:
        print(f"  ⚠️  Issues: {len(config_issues)}")
        all_issues.extend(config_issues)
    else:
        print("  ✅ Configuration OK")
    
    # Database patterns
    print("\n🗃️  Database Patterns...")
    db_issues = check_database_patterns()
    if db_issues:
        print(f"  ⚠️  Issues: {len(db_issues)}")
        all_issues.extend(db_issues)
    else:
        print("  ✅ Database patterns OK")
    
    # API patterns
    print("\n🌐 API Patterns...")
    api_issues = check_api_patterns()
    if api_issues:
        print(f"  ⚠️  Issues: {len(api_issues)}")
        all_issues.extend(api_issues)
    else:
        print("  ✅ API patterns OK")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    if all_issues:
        print(f"❌ Found {len(all_issues)} issues:")
        for issue in all_issues[:10]:  # Show first 10 issues
            print(f"  - {issue}")
        if len(all_issues) > 10:
            print(f"  ... and {len(all_issues) - 10} more issues")
        
        print("\n🔧 RECOMMENDATIONS:")
        print("- Fix security and error handling issues first")
        print("- Add comprehensive input validation")
        print("- Improve async patterns for better performance")
        print("- Add proper logging and monitoring")
        
        return 1
    else:
        print("✅ All validation checks passed!")
        print("\n🚀 PRODUCTION READINESS: GOOD")
        print("The multi-tenancy implementation follows best practices")
        return 0


if __name__ == "__main__":
    sys.exit(main())