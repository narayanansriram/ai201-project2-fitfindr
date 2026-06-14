"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: initialize session
    session = _new_session(query, wardrobe)

    print(f"\n{'─'*60}")
    print(f"  USER QUERY: \"{query}\"")
    print(f"{'─'*60}")

    # Step 2: parse query — extract size, price, and item description
    size_match = re.search(r'\bsize\s+([A-Za-z0-9/]+)', query, re.IGNORECASE)
    price_match = re.search(r'(?:under\s+)?\$(\d+(?:\.\d+)?)', query, re.IGNORECASE)
    size = size_match.group(1) if size_match else None
    max_price = float(price_match.group(1)) if price_match else None

    # Use only the first sentence so wardrobe context doesn't pollute the search
    first_sentence = re.split(r'[.!?]', query)[0]

    # Strip filler openers, size/price tokens, then clean whitespace
    description = re.sub(
        r"^(i'?m?\s+)?(looking for|searching for|find me|want|need)\s+(a\s+|an\s+)?",
        '', first_sentence, flags=re.IGNORECASE
    )
    description = re.sub(r'\bsize\s+[A-Za-z0-9/]+', '', description, flags=re.IGNORECASE)
    description = re.sub(r'under\s+\$?\d+(?:\.\d+)?', '', description, flags=re.IGNORECASE)
    description = re.sub(r'\$\d+(?:\.\d+)?', '', description)
    description = re.sub(r'\b(in|a|an|the)\b', '', description, flags=re.IGNORECASE)
    description = ' '.join(description.split())

    session["parsed"] = {"description": description, "size": size, "max_price": max_price}

    print(f"\n  [PLANNING LOOP] Parsed query:")
    print(f"    description : \"{description}\"")
    print(f"    size        : {size}")
    print(f"    max_price   : {max_price}")

    # Step 3: search listings, exit early if nothing found
    print(f"\n  [TOOL 1] Calling search_listings(description=\"{description}\", size={size}, max_price={max_price})")
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results

    if not results:
        session["error"] = (
            f"No listings found for '{description}'. "
            "Try a broader description or higher price limit."
        )
        print(f"\n  [PLANNING LOOP] search_listings returned 0 results → early exit")
        print(f"  [ERROR] {session['error']}")
        return session

    print(f"  [PLANNING LOOP] search_listings returned {len(results)} result(s) → selecting top match")

    # Step 4: select top result
    session["selected_item"] = results[0]
    item = session["selected_item"]
    print(f"\n  session[\"selected_item\"] set to:")
    print(f"    title : {item['title']}")
    print(f"    size  : {item['size']}  |  price : ${item['price']:.2f}  |  platform : {item.get('platform','')}")
    print(f"    desc  : {item['description']}")

    # Step 5: suggest outfit (proceeds even on fallback)
    wardrobe_count = len(session["wardrobe"].get("items", []))
    print(f"\n  [TOOL 2] Calling suggest_outfit(new_item=session[\"selected_item\"], wardrobe={wardrobe_count} item(s))")
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], session["wardrobe"])
    print(f"  [PLANNING LOOP] suggest_outfit returned → storing in session[\"outfit_suggestion\"]")
    print(f"\n  session[\"outfit_suggestion\"]:")
    for line in session["outfit_suggestion"].splitlines():
        print(f"    {line}")

    # Step 6: create fit card
    print(f"\n  [TOOL 3] Calling create_fit_card(outfit=session[\"outfit_suggestion\"], new_item=session[\"selected_item\"])")
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    print(f"  [PLANNING LOOP] create_fit_card returned → storing in session[\"fit_card\"]")
    print(f"\n  session[\"fit_card\"]:")
    print(f"    {session['fit_card']}")

    print(f"\n  [PLANNING LOOP] Done. session[\"error\"] = {session['error']}")
    print(f"{'─'*60}\n")

    # Step 7: return completed session
    return session


# ── CLI demo ──────────────────────────────────────────────────────────────────

def _print_session(session):
    sep = "─" * 60
    if session["error"]:
        print(f"  ❌  {session['error']}")
        return

    item = session["selected_item"]
    print(f"  Query parsed as:")
    print(f"    description : {session['parsed']['description']}")
    print(f"    size        : {session['parsed']['size']}")
    print(f"    max_price   : {session['parsed']['max_price']}")
    print()
    print(sep)
    print("  🛍️  TOP LISTING")
    print(sep)
    print(f"  {item['title']}")
    print(f"  Size: {item['size']}  |  ${item['price']:.2f}  |  {item.get('platform','').title()}  |  Condition: {item.get('condition','')}")
    print(f"  \"{item['description']}\"")
    print()
    print(sep)
    print("  👗  OUTFIT IDEA")
    print(sep)
    for line in session["outfit_suggestion"].splitlines():
        print(f"  {line}")
    print()
    print(sep)
    print("  ✨  FIT CARD")
    print(sep)
    print(f"  {session['fit_card']}")
    print()
    print(f"  [STATE CHECK]")
    print(f"  session['selected_item'] title     : {session['selected_item']['title']}")
    print(f"  session['outfit_suggestion'] first 60: {session['outfit_suggestion'][:60]}...")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    DIVIDER = "=" * 60

    print(DIVIDER)
    print("  DEMO 1 — full query with wardrobe context (happy path)")
    print(DIVIDER)
    session = run_agent(
        query="I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?",
        wardrobe=get_example_wardrobe(),
    )
    _print_session(session)

    print()
    print(DIVIDER)
    print("  DEMO 2 — empty wardrobe (fallback path)")
    print(DIVIDER)
    session2 = run_agent(
        query="vintage graphic tee under $30",
        wardrobe=get_empty_wardrobe(),
    )
    _print_session(session2)

    print()
    print(DIVIDER)
    print("  DEMO 3 — no results (early exit path)")
    print(DIVIDER)
    session3 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    _print_session(session3)
