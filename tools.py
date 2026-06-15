"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.
    """
    listings = load_listings()
    
    # Split description into lowercase keywords
    keywords = [kw.lower() for kw in description.split()] if description else []
    
    results = []
    for item in listings:
        # Price filter
        if max_price is not None:
            if item.get("price", 0.0) > max_price:
                continue
                
        # Size filter (flexible case-insensitive match)
        if size is not None:
            size_clean = size.strip().lower()
            item_size = item.get("size", "").lower()
            item_tags = [t.lower() for t in item.get("style_tags", [])]
            if size_clean not in item_size and size_clean not in item_tags:
                continue
                
        # Keyword matching
        if keywords:
            title_lower = item.get("title", "").lower()
            desc_lower = item.get("description", "").lower()
            tags_lower = [t.lower() for t in item.get("style_tags", [])]
            
            score = 0
            for kw in keywords:
                if kw in title_lower or kw in desc_lower or any(kw in tag for tag in tags_lower):
                    score += 1
                    
            if score == 0:
                continue
                
            item_copy = item.copy()
            item_copy["_score"] = score
            results.append(item_copy)
        else:
            item_copy = item.copy()
            item_copy["_score"] = 1
            results.append(item_copy)
            
    # Sort results by score (descending)
    results.sort(key=lambda x: x["_score"], reverse=True)
    
    # Strip the internal sorting key
    for r in results:
        r.pop("_score", None)
        
    return results


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(
    new_item: dict,
    wardrobe: dict,
    style_memory: str = "",
    trend_summary: str = "",
) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.
        style_memory: Historical user style preferences to respect.
        trend_summary: Trend information to incorporate.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.
    """
    client = _get_groq_client()
    
    # Check if wardrobe['items'] is empty
    is_empty = not wardrobe or not wardrobe.get("items")
    
    if is_empty:
        # Prompt for general versatile styling advice
        prompt = (
            f"Provide general, highly versatile styling tips, silhouette rules, and color coordination logic "
            f"optimized for this clothing item category: '{new_item.get('category')}' (specifically: '{new_item.get('title')}').\n"
            f"Description: {new_item.get('description')}\n"
            f"Vibe/Style Tags: {new_item.get('style_tags')}\n"
        )
    else:
        # Format wardrobe items
        wardrobe_list = []
        for item in wardrobe["items"]:
            colors = ", ".join(item.get("colors", []))
            tags = ", ".join(item.get("style_tags", []))
            notes = f" ({item.get('notes')})" if item.get("notes") else ""
            wardrobe_list.append(f"- {item.get('name')} in {colors} [style tags: {tags}]{notes}")
        wardrobe_str = "\n".join(wardrobe_list)
        
        prompt = (
            f"The user is looking to style a new item: '{new_item.get('title')}' (${new_item.get('price'):.2f} on {new_item.get('platform')}).\n"
            f"Description: {new_item.get('description')}\n"
            f"Vibe/Style Tags: {new_item.get('style_tags')}\n\n"
            f"The user's current wardrobe contains these items:\n{wardrobe_str}\n\n"
            f"Suggest 1-2 complete outfit combinations mixing and matching the new item with named pieces from their existing wardrobe.\n"
        )
        
    if style_memory:
        prompt += f"\nRespect the user's historical style preferences/keywords: {style_memory}.\n"
        
    if trend_summary:
        prompt += f"\nIncorporate the following trend insights into your suggestion: {trend_summary}.\n"
        
    prompt += "\nEnsure the suggestions are extremely aesthetic and versatile. Keep the entire response under 4 sentences total."
        
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a professional fashion stylist and coordinator."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return completion.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.
    """
    if not outfit or not outfit.strip():
        return "thrift find locked in! time to style it up. 🛍️✨"
        
    client = _get_groq_client()
    
    prompt = (
        f"You are a social media trendsetter creating an aesthetic post caption.\n"
        f"New Thrift Find: {new_item.get('title')} (${new_item.get('price'):.2f} on {new_item.get('platform')})\n"
        f"Vibe/Style Tags: {new_item.get('style_tags')}\n"
        f"Outfit Suggestion: {outfit}\n\n"
        f"Write a casual, authentic, social-media-ready caption (like a real OOTD post, not a product description) "
        f"based on the new thrift details and styling advice.\n"
        f"Rules:\n"
        f"- The caption must be strictly in lower-case letters.\n"
        f"- Mention the item name, price, and platform naturally (exactly once each).\n"
        f"- Include 1-2 relevant emojis.\n"
        f"- Keep it short, between 2 and 4 sentences."
    )
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a creative, trendy social media copywriter. You write strictly in lowercase letters."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.95
    )
    
    caption = completion.choices[0].message.content.strip()
    return caption.lower()


# ── Stretch Tool 4: compare_price ─────────────────────────────────────────────

def compare_price(new_item: dict) -> str:
    """
    Load the listings and calculate average price of items in the same category
    (and optionally brand if brand matches exist) and return a comparison message.
    """
    listings = load_listings()
    category = new_item.get("category")
    brand = new_item.get("brand")
    
    # Filter by category
    comparable_items = [item for item in listings if item.get("category") == category]
    
    # Optionally filter by brand
    if brand and str(brand).strip() not in ("", "None", "N/A"):
        brand_clean = str(brand).strip().lower()
        brand_filtered = [
            item for item in comparable_items 
            if item.get("brand") and item.get("brand").strip().lower() == brand_clean
        ]
        if brand_filtered:
            comparable_items = brand_filtered
            
    if not comparable_items:
        return f"No comparable items found to evaluate the price of this {category}."
        
    prices = [item.get("price", 0.0) for item in comparable_items]
    avg_price = sum(prices) / len(prices)
    new_price = new_item.get("price", 0.0)
    
    # Simple deal status logic
    if new_price < avg_price * 0.9:  # significantly lower
        deal_status = "a steal"
    elif new_price > avg_price * 1.1:  # significantly higher
        deal_status = "a bit above average"
    else:
        deal_status = "fairly priced"
        
    cat_display = category.lower() if category else "items"
    
    # Return formatted comparison message
    return f"At ${new_price:.2f}, this is {deal_status} compared to the average ${avg_price:.2f} for similar {cat_display}."


# ── Stretch Tool 5: get_trends ────────────────────────────────────────────────

def get_trends(category: str) -> str:
    """
    Ask Groq LLM (llama-3.3-70b-versatile) to act as a fashion trend analyst
    and summarize styling trends for the given category in contemporary streetwear.
    """
    client = _get_groq_client()
    
    prompt = (
        f"Act as a fashion trend analyst.\n"
        f"Return a 1-2 sentence summary of how items in the category '{category}' "
        f"are currently being styled in contemporary streetwear and thrift culture.\n"
        f"Keep the summary concise and direct."
    )
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a professional fashion trend analyst specializing in contemporary streetwear and thrift culture."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return completion.choices[0].message.content.strip()

