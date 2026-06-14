from unittest.mock import patch, MagicMock

from agent import run_agent

FAKE_ITEM = {
    "title": "Vintage Band Tee",
    "description": "Faded grey band tee, slightly oversized.",
    "size": "L",
    "price": 19.0,
    "category": "tops",
    "platform": "depop",
}
FAKE_WARDROBE = {"items": [{"name": "baggy jeans"}, {"name": "chunky sneakers"}]}
EMPTY_WARDROBE = {"items": []}


# ── branching on search_listings result ──────────────────────────────────────

def test_early_exit_when_no_results():
    """Loop must stop after search_listings if results are empty."""
    with patch("agent.search_listings", return_value=[]) as mock_search, \
         patch("agent.suggest_outfit") as mock_suggest, \
         patch("agent.create_fit_card") as mock_fit:

        session = run_agent("designer ballgown size XXS under $5", FAKE_WARDROBE)

        mock_search.assert_called_once()
        mock_suggest.assert_not_called()   # must NOT be called
        mock_fit.assert_not_called()       # must NOT be called
        assert session["error"] is not None
        assert session["outfit_suggestion"] is None
        assert session["fit_card"] is None


def test_all_tools_called_on_valid_query():
    """All three tools must run when search_listings returns results."""
    with patch("agent.search_listings", return_value=[FAKE_ITEM]), \
         patch("agent.suggest_outfit", return_value="wear it with jeans") as mock_suggest, \
         patch("agent.create_fit_card", return_value="thrift era activated") as mock_fit:

        session = run_agent("vintage tee under $30", FAKE_WARDROBE)

        mock_suggest.assert_called_once()
        mock_fit.assert_called_once()
        assert session["error"] is None


# ── session dict values ───────────────────────────────────────────────────────

def test_session_stores_selected_item():
    with patch("agent.search_listings", return_value=[FAKE_ITEM]), \
         patch("agent.suggest_outfit", return_value="some outfit"), \
         patch("agent.create_fit_card", return_value="some caption"):

        session = run_agent("vintage tee under $30", FAKE_WARDROBE)

        assert session["selected_item"] == FAKE_ITEM


def test_session_stores_outfit_suggestion():
    with patch("agent.search_listings", return_value=[FAKE_ITEM]), \
         patch("agent.suggest_outfit", return_value="wear it with jeans"), \
         patch("agent.create_fit_card", return_value="some caption"):

        session = run_agent("vintage tee under $30", FAKE_WARDROBE)

        assert session["outfit_suggestion"] == "wear it with jeans"


def test_session_stores_fit_card():
    with patch("agent.search_listings", return_value=[FAKE_ITEM]), \
         patch("agent.suggest_outfit", return_value="wear it with jeans"), \
         patch("agent.create_fit_card", return_value="thrift era activated"):

        session = run_agent("vintage tee under $30", FAKE_WARDROBE)

        assert session["fit_card"] == "thrift era activated"


def test_session_stores_error_on_no_results():
    with patch("agent.search_listings", return_value=[]):
        session = run_agent("designer ballgown", FAKE_WARDROBE)
        assert session["error"] is not None
        assert "No listings found" in session["error"]


# ── suggest_outfit receives selected_item, not re-parsed query ───────────────

def test_suggest_outfit_receives_selected_item():
    """suggest_outfit must be called with selected_item from session, not raw query."""
    with patch("agent.search_listings", return_value=[FAKE_ITEM]), \
         patch("agent.suggest_outfit", return_value="outfit") as mock_suggest, \
         patch("agent.create_fit_card", return_value="caption"):

        run_agent("vintage tee under $30", FAKE_WARDROBE)

        args, _ = mock_suggest.call_args
        assert args[0] == FAKE_ITEM   # first arg must be the item, not a string


# ── empty wardrobe proceeds to create_fit_card ───────────────────────────────

def test_empty_wardrobe_still_runs_create_fit_card():
    """Even with empty wardrobe, create_fit_card must still be called."""
    fallback = "Your wardrobe is empty — showing the item only."
    with patch("agent.search_listings", return_value=[FAKE_ITEM]), \
         patch("agent.suggest_outfit", return_value=fallback), \
         patch("agent.create_fit_card", return_value="caption") as mock_fit:

        session = run_agent("vintage tee under $30", EMPTY_WARDROBE)

        mock_fit.assert_called_once()
        assert session["fit_card"] == "caption"
