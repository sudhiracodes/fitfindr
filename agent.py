"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
"""

import re
from tools import search_listings, suggest_outfit, create_fit_card, compare_price, get_trends
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── query parser ──────────────────────────────────────────────────────────────

def parse_query(query: str) -> tuple[str, str | None, float | None]:
    """
    Extract budget caps and size patterns from the user query using regex.
    Returns (cleaned_description, size, max_price).
    """
    # Extract price (e.g. $30)
    price_match = re.search(r'\$(\d+(?:\.\d+)?)', query)
    max_price = None
    if price_match:
        max_price = float(price_match.group(1))

    # Extract size (e.g. size M, size large)
    size_match = re.search(r'size\s+([a-zA-Z0-9\-+/]+)', query, re.IGNORECASE)
    size = None
    if size_match:
        size = size_match.group(1)

    # Clean the query description
    cleaned_description = query
    if price_match:
        cleaned_description = cleaned_description.replace(price_match.group(0), "")
    if size_match:
        cleaned_description = cleaned_description.replace(size_match.group(0), "")

    # Remove filler/helper words near matches
    cleaned_description = re.sub(r'\bunder\b', '', cleaned_description, flags=re.IGNORECASE)
    cleaned_description = re.sub(r'\bin\b', '', cleaned_description, flags=re.IGNORECASE)

    # Clean extra whitespace and commas
    cleaned_description = re.sub(r'\s+', ' ', cleaned_description).strip()
    cleaned_description = cleaned_description.strip(",. ")

    return cleaned_description, size, max_price


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, use_empty_wardrobe: bool = False, style_memory: str = "") -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    # Initialize the central state dictionary
    session = {
        "query": query,
        "parsed_criteria": {},
        "selected_item": None,
        "outfit_suggestion": None,
        "fit_card": None,
        "warning": None,
        "price_comparison": None,
        "trends": None,
        "error": None
    }

    # Parse query and log in parsed_criteria
    cleaned_desc, size, max_price = parse_query(query)
    session["parsed_criteria"] = {
        "description": cleaned_desc,
        "size": size,
        "max_price": max_price
    }

    # Execute search
    results = search_listings(cleaned_desc, size, max_price)

    # Retry Logic with Fallback: After executing search_listings(), if the results list is empty,
    # trigger a second search_listings() call, passing only the cleaned_description
    if not results:
        results = search_listings(cleaned_desc, None, None)
        if results:
            session["warning"] = "No matches found with your size/price constraints, so we broadened the search to find similar items."

    # Planning loop logic: If no results found, abort early
    if not results:
        session["error"] = "No matching items found. Please try loosening your size filters or broadening your search keywords."
        return session

    # Assign top result to selected item
    session["selected_item"] = results[0]

    # Tool Orchestration: Call compare_price and get_trends
    category = session["selected_item"].get("category", "")
    session["price_comparison"] = compare_price(session["selected_item"])
    session["trends"] = get_trends(category)

    # Load wardrobe
    if use_empty_wardrobe:
        wardrobe = get_empty_wardrobe()
    else:
        wardrobe = get_example_wardrobe()

    # Sequentially call outfit suggestion and fit card generator
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"],
        wardrobe,
        style_memory=style_memory,
        trend_summary=session["trends"]
    )
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30, size M",
        use_empty_wardrobe=False,
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Parsed Criteria: {session['parsed_criteria']}")
        print(f"Found: {session['selected_item']['title']} (Price: ${session['selected_item']['price']}, Size: {session['selected_item']['size']})")
        print(f"Price Comparison: {session.get('price_comparison')}")
        print(f"Trends: {session.get('trends')}")
        if session.get("warning"):
            print(f"Warning: {session['warning']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        use_empty_wardrobe=False,
    )
    print(f"Parsed Criteria: {session2['parsed_criteria']}")
    print(f"Error message: {session2['error']}")

    print("\n\n=== Retry Fallback path ===\n")
    session3 = run_agent(
        query="vintage graphic tee under $5, size XXS",
        use_empty_wardrobe=False,
    )
    if session3["error"]:
        print(f"Error: {session3['error']}")
    else:
        print(f"Parsed Criteria: {session3['parsed_criteria']}")
        if session3.get("warning"):
            print(f"Warning: {session3['warning']}")
        print(f"Found: {session3['selected_item']['title']} (Price: ${session3['selected_item']['price']}, Size: {session3['selected_item']['size']})")
        print(f"Price Comparison: {session3.get('price_comparison')}")
        print(f"Trends: {session3.get('trends')}")
        print(f"\nOutfit: {session3['outfit_suggestion']}")
        print(f"\nFit card: {session3['fit_card']}")

