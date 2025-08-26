#!/usr/bin/env python3
"""
Script to fix timezone consistency issues in the automagik-omni codebase.
Replaces direct datetime calls with timezone-aware utilities from src.utils.datetime_utils.
"""

import os
import re
from pathlib import Path

def find_and_fix_timezone_issues():
    """Find and fix all timezone-related issues in the codebase."""
    
    # Files that need fixing based on analysis
    files_to_fix = {
        'src/services/discord_service.py': {
            'fixes': [
                {
                    'pattern': r"datetime\.now\(timezone\.utc\)",
                    'replacement': 'utcnow()',
                    'import_needed': True
                }
            ]
        },
        'src/channels/discord/interaction_handler.py': {
            'fixes': [
                {
                    'pattern': r"datetime\.utcnow\(\)",
                    'replacement': 'utcnow()',
                    'import_needed': True
                }
            ]
        },
        'src/channels/discord/utils.py': {
            'fixes': [
                {
                    'pattern': r"datetime\.utcnow\(\)",
                    'replacement': 'utcnow()',
                    'import_needed': True
                }
            ]
        },
        'src/channels/discord/webhook_notifier.py': {
            'fixes': [
                {
                    'pattern': r"datetime\.utcnow\(\)",
                    'replacement': 'utcnow()',
                    'import_needed': True
                }
            ]
        },
        'src/services/automagik_hive_models_fixed.py': {
            'fixes': [
                {
                    'pattern': r"datetime\.utcnow\(\)",
                    'replacement': 'utcnow()',
                    'import_needed': True
                }
            ]
        },
        'src/services/automagik_hive_models.py': {
            'fixes': [
                {
                    'pattern': r"datetime\.utcnow\(\)",
                    'replacement': 'utcnow()',
                    'import_needed': True
                }
            ]
        },
        'src/api/routes/instances.py': {
            'fixes': [
                {
                    'pattern': r"datetime\.now\(\)",
                    'replacement': 'utcnow()',
                    'import_needed': True
                }
            ]
        },
        'src/api/routes/instances_fixed.py': {
            'fixes': [
                {
                    'pattern': r"datetime\.now\(\)",
                    'replacement': 'utcnow()',
                    'import_needed': True
                }
            ]
        }
    }
    
    root_dir = Path('/home/cezar/automagik/automagik-omni')
    fixed_files = []
    
    for file_path, config in files_to_fix.items():
        full_path = root_dir / file_path
        
        if not full_path.exists():
            print(f"Warning: File {file_path} does not exist")
            continue
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes_made = False
            
            # Apply fixes
            for fix in config['fixes']:
                pattern = fix['pattern']
                replacement = fix['replacement']
                
                # Count matches before fixing
                matches = len(re.findall(pattern, content))
                if matches > 0:
                    content = re.sub(pattern, replacement, content)
                    changes_made = True
                    print(f"Fixed {matches} occurrences of {pattern} -> {replacement} in {file_path}")
            
            # Add import if needed and changes were made
            if changes_made and config['fixes'][0].get('import_needed', False):
                # Check if utcnow import already exists
                if 'from src.utils.datetime_utils import utcnow' not in content:
                    # Find the best place to add the import
                    import_patterns = [
                        r'(from src\.utils\.[^\n]+import [^\n]+)',
                        r'(from src\.[^\n]+import [^\n]+)',
                        r'(import [^\n]+)'
                    ]
                    
                    import_added = False
                    for pattern in import_patterns:
                        matches = list(re.finditer(pattern, content))
                        if matches:
                            # Find the last matching import in the first group
                            last_match = matches[-1]
                            insert_pos = content.find('\n', last_match.end()) + 1
                            if insert_pos > 0:
                                content = content[:insert_pos] + 'from src.utils.datetime_utils import utcnow\n' + content[insert_pos:]
                                import_added = True
                                print(f"Added utcnow import to {file_path}")
                                break
                    
                    if not import_added:
                        # Fall back to adding after the first import
                        if 'import ' in content:
                            first_import_pos = content.find('import ')
                            first_import_end = content.find('\n', first_import_pos)
                            if first_import_end != -1:
                                content = content[:first_import_end + 1] + 'from src.utils.datetime_utils import utcnow\n' + content[first_import_end + 1:]
                                print(f"Added utcnow import to {file_path} (fallback)")
            
            # Write back if changes were made
            if content != original_content:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(file_path)
                print(f"Successfully updated {file_path}")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return fixed_files

def show_current_issues():
    """Show current timezone issues in the codebase."""
    print("=== Current timezone issues analysis ===")
    
    patterns = [
        ('datetime.now(timezone.utc)', r'datetime\.now\(timezone\.utc\)'),
        ('datetime.utcnow()', r'datetime\.utcnow\(\)'),
        ('datetime.now()', r'datetime\.now\(\)')
    ]
    
    root_dir = Path('/home/cezar/automagik/automagik-omni')
    
    for pattern_name, pattern in patterns:
        print(f"\nLooking for: {pattern_name}")
        found_files = []
        
        for py_file in root_dir.rglob('*.py'):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.findall(pattern, content)
                    if matches:
                        relative_path = py_file.relative_to(root_dir)
                        found_files.append((str(relative_path), len(matches)))
            except:
                continue
        
        if found_files:
            for file_path, count in found_files:
                print(f"  {file_path}: {count} occurrences")
        else:
            print("  No issues found")

if __name__ == '__main__':
    print("Timezone consistency fix script for automagik-omni")
    print("=" * 50)
    
    # Show current issues
    show_current_issues()
    
    print("\n" + "=" * 50)
    print("Starting fixes...")
    
    fixed_files = find_and_fix_timezone_issues()
    
    print(f"\nCompleted! Fixed {len(fixed_files)} files:")
    for file_path in fixed_files:
        print(f"  ✓ {file_path}")
    
    if fixed_files:
        print("\n✅ All timezone issues have been fixed!")
        print("Now all timestamp operations use the centralized datetime_utils.utcnow() function.")
        print("\nNext steps:")
        print("1. Test the Discord service functionality")
        print("2. Verify all timestamps are timezone-aware and consistent")
        print("3. Check that existing functionality continues to work as expected")
    else:
        print("\n✅ No files needed fixing or all files were already using correct timezone utilities.")
    
    print("\n" + "=" * 50)
    print("Post-fix analysis:")
    show_current_issues()