#!/usr/bin/env python3
"""
Comprehensive verification script for WordStat application
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test all module imports"""
    print("="*80)
    print("TEST 1: MODULE IMPORTS")
    print("="*80)
    
    modules = [
        'utils.constants',
        'utils.logger',
        'storage.models',
        'storage.config_manager',
        'storage.state_manager',
        'storage.cache',
        'api.error_handler',
        'api.wordstat_client',
        'nlp.normalizer',
        'nlp.geo_cleaner',
        'filters.keyword_filters',
        'engine.rate_limiter',
        'engine.parser',
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except Exception as e:
            print(f"✗ {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n⚠ {len(failed)} modules failed to import")
        return False
    
    print("\n✓ All core modules imported successfully\n")
    return True


def test_rate_limiter_fix():
    """Test rate limiter validation fix"""
    print("="*80)
    print("TEST 2: RATE LIMITER VALIDATION FIX")
    print("="*80)
    
    from engine.rate_limiter import RateLimiter
    
    try:
        # This should work now (day >= hour)
        limiter = RateLimiter(max_rps=10, max_per_hour=1000, max_per_day=2000)
        print("✓ Allows max_per_day (2000) >= max_per_hour (1000)")
        
        # Test stats
        stats = limiter.get_stats()
        print(f"✓ Stats: {stats}")
        
        print("\n✓ Rate limiter fix verified\n")
        return True
    except Exception as e:
        print(f"✗ Rate limiter test failed: {e}")
        return False


def test_models_type_safety():
    """Test models type conversion"""
    print("="*80)
    print("TEST 3: MODELS TYPE SAFETY")
    print("="*80)
    
    from storage.models import KeywordData
    
    try:
        # Test string to int conversion
        kwd = KeywordData.from_dict({
            'phrase': 'test keyword',
            'count': '100',  # String
            'seed': 'test',
            'depth': '2',  # String
        })
        
        assert isinstance(kwd.count, int), "count should be int"
        assert kwd.count == 100, "count should be 100"
        assert isinstance(kwd.depth, int), "depth should be int"
        assert kwd.depth == 2, "depth should be 2"
        
        print("✓ String to int conversion works")
        
        # Test invalid values
        kwd2 = KeywordData.from_dict({
            'phrase': 'test',
            'count': 'invalid',
            'seed': 'test',
            'depth': None,
        })
        
        assert kwd2.count == 0, "Invalid count should default to 0"
        assert kwd2.depth == 1, "Invalid depth should default to 1"
        
        print("✓ Invalid value handling works")
        print("\n✓ Model type safety verified\n")
        return True
    
    except Exception as e:
        print(f"✗ Models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_resource_management():
    """Test cache database resource management"""
    print("="*80)
    print("TEST 4: CACHE RESOURCE MANAGEMENT")
    print("="*80)
    
    from storage.cache import WordstatCache
    import os
    import tempfile
    
    try:
        # Create temp db
        temp_db = os.path.join(tempfile.gettempdir(), 'test_cache.db')
        
        # Remove if exists
        if os.path.exists(temp_db):
            os.remove(temp_db)
        
        # Initialize cache
        cache = WordstatCache(db_path=temp_db, ttl_days=1)
        print("✓ Cache initialized")
        
        # Test set/get
        test_data = [{'phrase': 'test', 'count': 100}]
        cache.set('test_phrase', test_data)
        print("✓ Cache set works")
        
        result = cache.get('test_phrase')
        assert result == test_data, "Retrieved data should match"
        print("✓ Cache get works")
        
        # Test stats
        stats = cache.get_stats()
        print(f"✓ Cache stats: {stats}")
        
        # Cleanup
        cache.shutdown()
        print("✓ Cache shutdown works")
        
        # Verify DB file exists and is not corrupted
        assert os.path.exists(temp_db), "DB file should exist"
        print("✓ DB file exists")
        
        # Cleanup
        if os.path.exists(temp_db):
            os.remove(temp_db)
            print("✓ Cleanup successful")
        
        print("\n✓ Cache resource management verified\n")
        return True
    
    except Exception as e:
        print(f"✗ Cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_keyword_filter():
    """Test keyword filter functionality"""
    print("="*80)
    print("TEST 5: KEYWORD FILTER")
    print("="*80)
    
    from filters.keyword_filters import KeywordFilter
    
    try:
        kf = KeywordFilter()
        print("✓ KeywordFilter initialized")
        
        # Test basic filtering
        kf.set_min_count(10)
        kf.set_word_range(1, 5)
        
        # Test with valid keyword
        passed, reason = kf.apply("test keyword", 100)
        assert passed, "Should pass valid keyword"
        print("✓ Valid keyword passes")
        
        # Test with low count
        passed, reason = kf.apply("test keyword", 5)
        assert not passed, "Should reject low count"
        print(f"✓ Low count rejected: {reason}")
        
        # Test with too many words
        passed, reason = kf.apply("word1 word2 word3 word4 word5 word6", 100)
        assert not passed, "Should reject too many words"
        print(f"✓ Too many words rejected: {reason}")
        
        print("\n✓ Keyword filter verified\n")
        return True
    
    except Exception as e:
        print(f"✗ Keyword filter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_normalizer():
    """Test text normalizer"""
    print("="*80)
    print("TEST 6: TEXT NORMALIZER")
    print("="*80)
    
    from nlp.normalizer import get_normalizer
    
    try:
        normalizer = get_normalizer()
        print("✓ Normalizer initialized")
        
        # Test normalization
        phrase = "  TEST  Keyword  123  "
        normalized = normalizer.normalize_phrase(phrase)
        assert normalized == "test keyword 123", f"Expected 'test keyword 123', got '{normalized}'"
        print(f"✓ Normalization: '{phrase}' -> '{normalized}'")
        
        # Test validation
        assert normalizer.is_valid_keyword("valid keyword"), "Should be valid"
        assert not normalizer.is_valid_keyword(""), "Empty should be invalid"
        print("✓ Validation works")
        
        print("\n✓ Normalizer verified\n")
        return True
    
    except Exception as e:
        print(f"✗ Normalizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("WORDSTAT APPLICATION VERIFICATION")
    print("="*80 + "\n")
    
    tests = [
        ("Module Imports", test_imports),
        ("Rate Limiter Fix", test_rate_limiter_fix),
        ("Models Type Safety", test_models_type_safety),
        ("Cache Resource Management", test_cache_resource_management),
        ("Keyword Filter", test_keyword_filter),
        ("Text Normalizer", test_normalizer),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}\n")
            results.append((name, False))
    
    # Summary
    print("="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12s} {name}")
    
    print("="*80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*80)
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
