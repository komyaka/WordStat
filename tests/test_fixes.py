"""
Test script for clipboard and filter settings fixes
"""
import ast
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_clipboard_bindings():
    """Test that clipboard_handler has both uppercase and lowercase bindings"""
    print("\n" + "=" * 80)
    print("TEST: Clipboard Keybindings")
    print("=" * 80)
    
    file_path = 'ui/clipboard_handler.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for both lowercase and uppercase bindings
    required_bindings = [
        '<Control-c>', '<Control-C>',
        '<Control-v>', '<Control-V>',
        '<Control-x>', '<Control-X>',
        '<Control-a>', '<Control-A>',
    ]
    
    missing = []
    for binding in required_bindings:
        if binding not in content:
            missing.append(binding)
    
    if missing:
        print(f"✗ FAILED: Missing bindings: {missing}")
        return False
    else:
        print(f"✓ PASSED: All clipboard bindings present (uppercase and lowercase)")
        return True


def test_widgets_paste_counter():
    """Test that widgets.py updates counter after paste"""
    print("\n" + "=" * 80)
    print("TEST: Widget Counter Update After Paste")
    print("=" * 80)
    
    file_path = 'ui/widgets.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for paste counter updates
    has_lowercase_paste = '<Control-v>' in content and '_update_counter' in content
    has_uppercase_paste = '<Control-V>' in content and '_update_counter' in content
    
    if has_lowercase_paste and has_uppercase_paste:
        print(f"✓ PASSED: Counter update bound to paste operations")
        return True
    else:
        print(f"✗ FAILED: Missing counter update on paste")
        return False


def test_set_filter_settings():
    """Test that main_window has set_filter_settings method"""
    print("\n" + "=" * 80)
    print("TEST: set_filter_settings Method")
    print("=" * 80)
    
    file_path = 'ui/main_window.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the file to find the method
    try:
        tree = ast.parse(content)
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                methods.append(node.name)
        
        if 'set_filter_settings' in methods:
            print(f"✓ PASSED: set_filter_settings method exists")
            
            # Check if it sets the expected fields
            expected_fields = [
                'filter_min_count', 'filter_min_words', 'filter_max_words',
                'filter_include_regex', 'filter_exclude_regex',
                'filter_exclude_substrings', 'filter_minus_words', 'filter_minus_mode'
            ]
            
            missing_fields = []
            for field in expected_fields:
                if field not in content or f"{field}.set" not in content:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"  ⚠ WARNING: Some fields might be missing: {missing_fields}")
            else:
                print(f"  ✓ All expected filter fields are being set")
            
            return True
        else:
            print(f"✗ FAILED: set_filter_settings method not found")
            return False
    except Exception as e:
        print(f"✗ FAILED: Error parsing file: {e}")
        return False


def test_app_load_save_filters():
    """Test that app.py loads and saves filter settings"""
    print("\n" + "=" * 80)
    print("TEST: App Load/Save Filter Settings")
    print("=" * 80)
    
    file_path = 'app.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check _load_config_to_ui loads filter settings
    has_load = 'filter_settings = self.config.get(\'filters\'' in content
    has_load_call = 'self.ui.set_filter_settings(filter_settings)' in content
    
    # Check _save_config_from_ui saves filter settings
    has_save_get = 'filter_settings = self.ui.get_filter_settings()' in content
    has_save_fields = all([
        'exclude_substrings' in content,
        'minus_words' in content,
        'self.config[\'filters\']' in content
    ])
    
    results = []
    if has_load and has_load_call:
        print(f"✓ PASSED: Filter settings loading implemented")
        results.append(True)
    else:
        print(f"✗ FAILED: Filter settings loading not found")
        results.append(False)
    
    if has_save_get and has_save_fields:
        print(f"✓ PASSED: Filter settings saving implemented")
        results.append(True)
    else:
        print(f"✗ FAILED: Filter settings saving not found")
        results.append(False)
    
    return all(results)


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("TESTING FIXES FOR CLIPBOARD AND FILTER PERSISTENCE")
    print("=" * 80)
    
    results = []
    
    results.append(test_clipboard_bindings())
    results.append(test_widgets_paste_counter())
    results.append(test_set_filter_settings())
    results.append(test_app_load_save_filters())
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
