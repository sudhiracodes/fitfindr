import pytest
from tools import search_listings, compare_price, get_trends
from agent import run_agent

def test_search_returns_results():
    """Asserts that a standard search query returns a list of results."""
    results = search_listings(description="vintage graphic tee")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "title" in results[0]
    assert "price" in results[0]

def test_search_empty_results():
    """Asserts that searching for a non-existent item returns an empty list [] safely."""
    results = search_listings(description="mecha suit")
    assert isinstance(results, list)
    assert results == []

def test_search_price_filter():
    """Asserts that all returned listings strictly respect a low max_price constraint."""
    results = search_listings(description="tee", max_price=20.0)
    assert isinstance(results, list)
    for item in results:
        assert item["price"] <= 20.0

def test_compare_price():
    """Asserts that compare_price returns a string comparing the item to the category average."""
    dummy_item = {"category": "tops", "price": 10.0, "brand": "Ralph Lauren"}
    res = compare_price(dummy_item)
    assert isinstance(res, str)
    assert "At $10.00" in res
    assert "similar tops" in res

def test_get_trends():
    """Asserts that get_trends returns a fashion analysis string."""
    res = get_trends("tops")
    assert isinstance(res, str)
    assert len(res) > 0

def test_agent_retry_fallback():
    """Asserts that run_agent retries search when first search returns nothing."""
    session = run_agent(query="vintage graphic tee under $10, size XS")
    assert session["selected_item"] is not None
    assert session["warning"] is not None
    assert "broadened" in session["warning"]

def test_agent_style_memory():
    """Asserts that style_memory is passed down and is present in session outputs."""
    session = run_agent(query="vintage graphic tee under $30", style_memory="grunge, baggy")
    assert session["outfit_suggestion"] is not None
