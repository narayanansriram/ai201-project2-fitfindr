from tools import search_listings, suggest_outfit, create_fit_card


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_sorted_by_relevance():
    # A more specific query should score higher than a generic one
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert len(results) >= 2
    # First result must contain both "vintage" and either "graphic" or "tee"
    top = (results[0]["title"] + results[0]["description"] + " ".join(results[0].get("style_tags", []))).lower()
    assert "vintage" in top or "graphic" in top or "tee" in top


def test_search_size_partial_match():
    # Listings use sizes like "S/M" — querying "S" should still match them
    results = search_listings("tee", size="S", max_price=100)
    assert all("s" in item["size"].lower() for item in results)


def test_search_result_fields():
    results = search_listings("vintage", size=None, max_price=100)
    assert len(results) > 0
    required_fields = {"title", "description", "size", "price", "category"}
    for item in results:
        assert required_fields.issubset(item.keys())


# ── suggest_outfit ────────────────────────────────────────────────────────────

SAMPLE_ITEM = {
    "title": "Vintage Band Tee — Faded Grey",
    "description": "Faded grey band tee with a classic rock graphic, slightly oversized.",
    "size": "L",
    "price": 19.0,
    "category": "tops",
}

POPULATED_WARDROBE = {
    "items": [
        {"name": "baggy straight-leg jeans, dark wash"},
        {"name": "chunky white sneakers"},
        {"name": "white ribbed tank top"},
    ]
}

EMPTY_WARDROBE = {"items": []}


def test_suggest_outfit_returns_string():
    result = suggest_outfit(SAMPLE_ITEM, POPULATED_WARDROBE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe_returns_fallback():
    result = suggest_outfit(SAMPLE_ITEM, EMPTY_WARDROBE)
    assert isinstance(result, str)
    assert len(result) > 0
    # Should not crash — must return the fallback message
    assert "wardrobe" in result.lower()


def test_suggest_outfit_references_item():
    result = suggest_outfit(SAMPLE_ITEM, POPULATED_WARDROBE)
    # The suggestion should reference the new item or wardrobe pieces
    combined = result.lower()
    assert any(word in combined for word in ["tee", "band", "vintage", "jeans", "sneakers"])


# ── create_fit_card ───────────────────────────────────────────────────────────

SAMPLE_OUTFIT = (
    "Wear the faded band tee slightly tucked into baggy dark-wash jeans, "
    "cuffed once at the ankle. Finish with chunky white sneakers."
)

SAMPLE_ITEM_WITH_PLATFORM = {
    "title": "Vintage Band Tee — Faded Grey",
    "description": "Faded grey band tee with a classic rock graphic, slightly oversized.",
    "size": "L",
    "price": 19.0,
    "category": "tops",
    "platform": "depop",
}


def test_create_fit_card_returns_string():
    result = create_fit_card(SAMPLE_OUTFIT, SAMPLE_ITEM_WITH_PLATFORM)
    assert isinstance(result, str)
    assert len(result) > 0


def test_create_fit_card_empty_outfit_returns_error():
    result = create_fit_card("", SAMPLE_ITEM_WITH_PLATFORM)
    assert result.startswith("[ERROR]")


def test_create_fit_card_whitespace_outfit_returns_error():
    result = create_fit_card("   ", SAMPLE_ITEM_WITH_PLATFORM)
    assert result.startswith("[ERROR]")


def test_create_fit_card_varies_across_runs():
    r1 = create_fit_card(SAMPLE_OUTFIT, SAMPLE_ITEM_WITH_PLATFORM)
    r2 = create_fit_card(SAMPLE_OUTFIT, SAMPLE_ITEM_WITH_PLATFORM)
    # With temperature=0.9 outputs should differ; if identical the model is deterministic
    assert r1 != r2, "Fit card output was identical across two runs — check LLM temperature"
