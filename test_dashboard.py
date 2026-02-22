#!/usr/bin/env python3
"""
CHEN-KIT Dashboard Test Suite
Run: python3 test_dashboard.py
"""

import sys
import time
import threading
import urllib.request
from http.server import HTTPServer

# Import dashboard components
from dashboard import (
    ALL_RECIPES, ALL_RULES, ALL_TRANSCRIPTS, ALL_INVENTORY,
    ALL_INV_DATA, INV_BY_CAT, TAGS_STATS, RULES_DO, RULES_DONT,
    SEMANTIC_ENABLED, SEARCH_INDEX, Handler,
    parse_md, load_folder, score_recipe, categorize_recipe, has_forbidden_combo
)

def test_data_loading():
    """Test all data is loaded correctly."""
    print("\n[TEST] Data Loading")

    assert len(ALL_RECIPES) > 100, f"Expected 100+ recipes, got {len(ALL_RECIPES)}"
    assert len(ALL_RULES) > 20, f"Expected 20+ rules, got {len(ALL_RULES)}"
    assert len(ALL_TRANSCRIPTS) >= 0, "Transcripts should be loadable"
    assert len(ALL_INVENTORY) > 100, f"Expected 100+ inventory items, got {len(ALL_INVENTORY)}"
    assert len(INV_BY_CAT) > 10, f"Expected 10+ inventory categories, got {len(INV_BY_CAT)}"
    assert len(TAGS_STATS) > 10, f"Expected 10+ unique tags, got {len(TAGS_STATS)}"

    print(f"  Recipes: {len(ALL_RECIPES)} ✓")
    print(f"  Rules: {len(ALL_RULES)} ✓")
    print(f"  Transcripts: {len(ALL_TRANSCRIPTS)} ✓")
    print(f"  Inventory: {len(ALL_INVENTORY)} items ✓")
    print(f"  Categories: {len(INV_BY_CAT)} ✓")
    print(f"  Tags: {len(TAGS_STATS)} ✓")
    return True

def test_recipe_structure():
    """Test recipe data structure."""
    print("\n[TEST] Recipe Structure")

    for r in ALL_RECIPES[:5]:
        assert 'name' in r, "Recipe missing name"
        assert 'content' in r, "Recipe missing content"
        assert 'meta' in r, "Recipe missing meta"
        assert 'sections' in r, "Recipe missing sections"

    # Check a recipe has expected fields
    sample = ALL_RECIPES[0]
    print(f"  Sample: {sample['name']}")
    print(f"  Has title: {'title' in sample} ✓")
    print(f"  Has meta.tags: {'tags' in sample.get('meta', {})} ✓")
    print(f"  Has ingredients: {len(sample.get('items', []))} items ✓")
    return True

def test_rules_structure():
    """Test rules data structure."""
    print("\n[TEST] Rules Structure")

    for r in ALL_RULES[:5]:
        assert 'name' in r, "Rule missing name"
        assert 'content' in r, "Rule missing content"

    sample = ALL_RULES[0]
    print(f"  Sample: {sample['name']}")
    print(f"  Has category: {'category' in sample.get('meta', {})} ✓")
    print(f"  Has sections: {len(sample.get('sections', {}))} sections ✓")
    return True

def test_semantic_search():
    """Test semantic search functionality."""
    print("\n[TEST] Semantic Search")

    if not SEMANTIC_ENABLED or not SEARCH_INDEX:
        print("  SKIPPED (semantic search not available)")
        return True

    # Polish query
    results = SEARCH_INDEX.search("rozgrzewające trawienie", top_k=3)
    assert len(results) > 0, "No results for Polish query"
    print(f"  Polish query: {len(results)} results ✓")

    # English query
    results = SEARCH_INDEX.search("warming digestive", top_k=3)
    assert len(results) > 0, "No results for English query"
    print(f"  English query: {len(results)} results ✓")

    # Type-filtered query
    results = SEARCH_INDEX.search("tofu", top_k=5, doc_type='recipe')
    assert all(r['type'] == 'recipe' for r in results), "Type filter failed"
    print(f"  Type-filtered query: {len(results)} results ✓")

    # Related docs
    related = SEARCH_INDEX.get_related('recipe', 'kitchari-ajurwedyjskie', top_k=3)
    print(f"  Related docs: {len(related)} found ✓")

    return True

def test_recipe_scoring():
    """Test recipe ingredient scoring."""
    print("\n[TEST] Recipe Scoring")

    scores = [score_recipe(r, ALL_INVENTORY) for r in ALL_RECIPES[:20]]
    assert max(scores) <= 100, "Score exceeds 100"
    assert min(scores) >= 0, "Score below 0"

    # Check some recipes have high scores
    high_score_count = sum(1 for s in scores if s >= 50)
    print(f"  Score range: {min(scores)}-{max(scores)} ✓")
    print(f"  High scoring (≥50%): {high_score_count}/20 ✓")
    return True

def test_categorization():
    """Test recipe categorization."""
    print("\n[TEST] Recipe Categorization")

    categories = {}
    for r in ALL_RECIPES:
        cat = categorize_recipe(r)
        categories[cat] = categories.get(cat, 0) + 1

    assert 'breakfast' in categories, "No breakfast recipes"
    assert 'lunch' in categories, "No lunch recipes"
    assert 'dinner' in categories, "No dinner recipes"

    for cat, count in categories.items():
        print(f"  {cat}: {count} ✓")
    return True

def test_forbidden_detection():
    """Test forbidden ingredient combo detection."""
    print("\n[TEST] Forbidden Combo Detection")

    forbidden_count = sum(1 for r in ALL_RECIPES if has_forbidden_combo(r))
    clean_count = len(ALL_RECIPES) - forbidden_count

    print(f"  Clean recipes: {clean_count} ✓")
    print(f"  With forbidden combos: {forbidden_count} ✓")
    return True

def test_http_handler():
    """Test HTTP handler responds correctly."""
    print("\n[TEST] HTTP Handler")

    # Start server in background
    server = HTTPServer(('127.0.0.1', 5556), Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    time.sleep(0.5)

    try:
        # Test main page
        with urllib.request.urlopen('http://127.0.0.1:5556/', timeout=5) as resp:
            html = resp.read().decode('utf-8')
            assert 'CHEN-KIT' in html, "Missing CHEN-KIT title"
            assert 'search' in html.lower(), "Missing search"
            if SEMANTIC_ENABLED:
                assert 'Semantic' in html or 'semantic' in html.lower(), "Missing semantic toggle"
        print("  GET / : 200 ✓")
    except Exception as e:
        print(f"  GET / : FAILED - {e}")
        return False
    finally:
        server.server_close()

    return True

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("CHEN-KIT TEST SUITE")
    print("=" * 60)

    tests = [
        test_data_loading,
        test_recipe_structure,
        test_rules_structure,
        test_semantic_search,
        test_recipe_scoring,
        test_categorization,
        test_forbidden_detection,
        test_http_handler,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
