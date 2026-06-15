"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── Style Keywords & Query Handler ───────────────────────────────────────────

import re

STYLE_KEYWORDS = {
    "grunge", "y2k", "baggy", "vintage", "classic", "denim", "streetwear", 
    "cottagecore", "flannel", "layering", "athletic", "earth tones", "70s", 
    "band tee", "goth", "platform", "90s", "color block", "cargo", "2000s", 
    "feminine", "floral", "western", "summer", "minimal", "cozy", "oversized", 
    "knitwear", "preppy", "dark academia", "workwear", "statement", "glam", 
    "customized", "rock", "tie-dye", "colorful"
}

def handle_query(user_query: str, wardrobe_choice: str, state_memory: str) -> tuple[str, str, str, str, str, any]:
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:     The text the user typed into the search box.
        wardrobe_choice: Either "Example wardrobe" or "Empty wardrobe (new user)".
        state_memory:   The accumulated style preferences string from gr.State.

    Returns:
        A tuple of values mapping to the UI outputs.
    """
    if state_memory is None:
        state_memory = ""

    # 1. Guard against empty/whitespace query
    if not user_query or not user_query.strip():
        return (
            "Please enter what you are looking for to begin! 🛍️", 
            "N/A", 
            "N/A", 
            state_memory, 
            state_memory, 
            gr.update(visible=False, value="")
        )

    # 2. Extract style keywords and update memory state
    query_lower = user_query.lower()
    extracted_keywords = []
    for kw in STYLE_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
            extracted_keywords.append(kw)
            
    if extracted_keywords:
        existing_keywords = [k.strip() for k in state_memory.split(",") if k.strip()]
        for kw in extracted_keywords:
            if kw not in existing_keywords:
                existing_keywords.append(kw)
        state_memory = ", ".join(existing_keywords)

    # 3. Determine empty wardrobe flag
    use_empty_wardrobe = (wardrobe_choice == "Empty wardrobe (new user)")

    # 4. Call run_agent
    session = run_agent(user_query, use_empty_wardrobe=use_empty_wardrobe, style_memory=state_memory)

    # 5. Handle early errors/abort
    if session.get("error"):
        return (
            session["error"], 
            "N/A", 
            "N/A", 
            state_memory, 
            state_memory, 
            gr.update(visible=False, value="")
        )

    # 6. Format successful result
    item = session["selected_item"]
    if not item:
        return (
            "No item was selected.", 
            "N/A", 
            "N/A", 
            state_memory, 
            state_memory, 
            gr.update(visible=False, value="")
        )

    brand = item.get("brand") or "N/A"
    listing_text = (
        f"Title: {item.get('title')}\n"
        f"Brand: {brand}\n"
        f"Price: ${item.get('price'):.2f}\n"
        f"Condition: {item.get('condition')}\n"
        f"Platform: {item.get('platform')}"
    )
    if session.get("price_comparison"):
        listing_text += f"\n\nPrice Evaluation:\n{session['price_comparison']}"

    warning = session.get("warning")
    warning_update = gr.update(value=warning, visible=True) if warning else gr.update(value="", visible=False)

    return (
        listing_text,
        session.get("outfit_suggestion") or "",
        session.get("fit_card") or "",
        state_memory,
        state_memory,
        warning_update
    )


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        # gr.State stores historical user style profile memory
        memory_state = gr.State(value="")

        # Warning output banner (rendered if retry logic triggered)
        warning_output = gr.Textbox(
            label="⚠️ Notice",
            value="",
            visible=False,
            interactive=False,
        )

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        # Style preferences tracker element
        style_memory_display = gr.Textbox(
            label="🧠 Remembered Style Preferences (Persistent Profile Memory)",
            value="",
            interactive=False,
            placeholder="No style preferences remembered yet. (e.g. y2k, grunge, baggy)"
        )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        # Submit handlers
        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice, memory_state],
            outputs=[listing_output, outfit_output, fitcard_output, memory_state, style_memory_display, warning_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice, memory_state],
            outputs=[listing_output, outfit_output, fitcard_output, memory_state, style_memory_display, warning_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
