# FitFindr — Multi-Tool Agentic Styling Workflow

FitFindr is an intelligent, multi-tool AI styling assistant that helps users discover secondhand fashion listings, receive curated outfit combinations, and generate social media-ready "fit cards." 

Rather than acting as a simple LLM wrapper, FitFindr utilizes a deterministic orchestrator loop that manages complex state transitions, handles restrictive searches with graceful fallbacks, evaluates real-time data metrics, and learns user style preferences dynamically over continuous interactions.

---

## 🛠️ Tool Inventory

FitFindr's architecture separates core capabilities into distinct, isolated tools within `tools.py`. This ensures testability, modularity, and strict input/output verification.

### Core Architecture Tools
* **`search_listings(description: str, size: str = None, max_price: float = None) -> list[dict]`**
    * *Purpose:* Queries the local secondhand clothing dataset (`listings.json`).
    * *Engine:* Uses token-based keyword scoring, flexible string-matching for sizes, and numerical bounds for budget filtering.
    * *Failure Guard:* Returns an empty list (`[]`) rather than crashing or throwing an error if no records match.
* **`suggest_outfit(new_item: dict, wardrobe: dict, style_memory: str = "", trend_summary: str = "") -> str`**
    * *Purpose:* Combines a newly found item with the user's existing wardrobe to propose a cohesive look.
    * *Engine:* Powered by Groq SDK using the `llama-3.3-70b-versatile` model.
    * *Failure Guard:* Contains a critical failure guard for empty wardrobes. If the user's wardrobe is empty, it dynamically pivots its system prompt to output general, high-level style rules instead of failing.
* **`create_fit_card(outfit: str, new_item: dict) -> str`**
    * *Purpose:* Automatically designs a casual social media caption highlighting the look.
    * *Engine:* Uses Groq with a high creative variation parameter (`temperature=0.95`).
    * *Failure Guard:* If inputs are missing or empty, it defaults cleanly to an aesthetic placeholder text. Post-processes all generation directly to lowercase to match modern thrift culture curation.

### Advanced Stretch Feature Tools
* **`compare_price(new_item: dict) -> str`**
    * *Purpose:* Acts as a localized data intelligence layer evaluating thrift deals.
    * *Engine:* Dynamically filters the `listings.json` database across matching categories and brand metrics to calculate localized market averages, returning a direct comparison string.
* **`get_trends(category: str) -> str`**
    * *Purpose:* Extracts micro-trends based on specific clothing categories.
    * *Engine:* Prompts `llama-3.3-70b-versatile` to act as a streetwear and thrifting subculture analyst, generating 1-2 concise contextual sentences.

---

## 🧠 The Planning Loop & Orchestration

The brain of the agent resides in `agent.py` under the `run_agent()` planning pipeline. It orchestrates state progression based on live feedback:

1.  **Input Parsing:** The orchestrator extracts explicit parameters from the natural language query using regular expressions (e.g., targeting price points like `under $40` and standard sizing filters).
2.  **Retry Logic with Fallback:** If the primary tool execution of `search_listings` returns an empty set due to highly restrictive parameters, the orchestrator triggers an automated fallback branch. It strips out the `size` and `max_price` constraints, runs a broadened fallback search, and logs a descriptive notification warning to the user state without breaking execution.
3.  **Parallel Execution & Pipeline Chaining:** Once an item is successfully isolated, its specific metadata is dispatched simultaneously to downstream data utilities (`compare_price`) and trend synthesis loops (`get_trends`).

---

## 💾 State Management & Persistence

FitFindr handles session data dynamically through two layers of state:

* **Central Session Dictionary:** A unified dictionary structure (`session = {}`) tracks execution attributes step-by-step (`query`, `parsed_criteria`, `selected_item`, `outfit_suggestion`, `fit_card`, `error`, `warning`, `price_comparison`, `trends`). This removes data fragmentation and ensures downstream text-generation tools have access to up-to-date payload parameters without prompting the user to repeat information.
* **Style Profile Memory (`gr.State`):** To prevent contextual amnesia across continuous chat interactions, the Gradio user interface implements a persistent memory layer. The application continuously scans queries against a static set of style keywords. Extracted tags append directly to the persistent `gr.State` block and are injected straight into subsequent LLM prompts, mapping a growing profile of user aesthetic preferences over time.

---

## 🛡️ Error Handling Case Studies

To ensure structural stability, FitFindr explicitly implements structural guards validated through our `pytest` testing suite:

1.  **Case Study: The Hyper-Restrictive Query**
    * *Input:* `"y2k cargo pants under $5 size XXS"` (Yields zero original listing matches).
    * *Handling:* System automatically intercepts the empty array, clears the numerical constraints, falls back to a broad description query, registers `session["warning"]`, and visualizes the notification alert clearly in the UI.
2.  **Case Study: The Fresh Wardrobe Profile**
    * *Input:* An unpopulated wardrobe payload (`empty_wardrobe` dataset template).
    * *Handling:* `suggest_outfit` intercepts the lack of items, switches off its specific matching system prompt, and deploys generalized color coordination theory guidelines instead.

---

## 🤖 AI Usage Reflection

During the development lifecycle, generative AI tools were leveraged strategically across two key inflection points:

* **Refined Pytest Suite Architecture:** AI was utilized to draft structural mock assertions inside `tests/test_tools.py`. By explicitly prompting for extreme boundary value conditions (such as handling empty lists and tracking data variations across specific float parameters for price bounds), comprehensive test coverage was built for the core filtering utilities.
* **Multi-Feature Scaling Strategy:** When scaling from the core MVP to incorporating four complex stretch features simultaneously, an AI assistant was prompted to structure the design patterns. By constraining the AI to design with optional keyword arguments with standard fallback strings (e.g., `style_memory: str = ""`), contextual memory injection and trend analytics were effectively introduced without breaking backward-compatibility interfaces or fracturing automated evaluation suites.

---

## 🚀 Setup & Execution

### Installation
Activate your virtual environment and install the required dependencies:
```bash
source .venv/bin/activate
pip install -r requirements.txt