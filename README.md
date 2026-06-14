# FitFindr

An AI agent that searches secondhand clothing listings and generates outfit suggestions and shareable captions based on a user's existing wardrobe.

---

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## Running the App

```bash
python app.py
```

Then open the URL shown in your terminal (usually `http://localhost:7860`).

## Running Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

---

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) → list[dict]`

Searches `data/listings.json` for secondhand items matching the user's query. Filters by price and size first, then scores remaining listings by keyword overlap across `title`, `description`, and `style_tags`. Items with a score of zero are dropped; the rest are returned sorted by relevance, highest first.

- **description** (str): Keywords describing the item (e.g. `"vintage graphic tee"`)
- **size** (str | None): Size to filter by (e.g. `"M"`, `"S/M"`). Pass `None` to skip size filtering. Matching is case-insensitive and substring-based, so `"S"` matches listings sized `"S/M"`.
- **max_price** (float | None): Price ceiling, inclusive. Pass `None` to skip price filtering.
- **Returns**: A list of matching listing dicts. Each dict contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Returns `[]` if nothing matches — never raises an exception.

---

### `suggest_outfit(new_item: dict, wardrobe: dict) → str`

Calls the Groq LLM (`llama-3.3-70b-versatile`) to suggest 1–2 complete outfit combinations that incorporate the thrifted item and named pieces from the user's wardrobe.

- **new_item** (dict): A listing dict from `search_listings` — must contain `title`, `description`, `size`, `price`, `category`.
- **wardrobe** (dict): A wardrobe dict with an `"items"` key mapping to a list of wardrobe item dicts (each with a `"name"` field).
- **Returns**: A non-empty string with outfit suggestions. If `wardrobe["items"]` is empty or the LLM returns blank, returns the fallback string: `"Your wardrobe is empty — we can still show you the item, but can't suggest a full outfit. Try adding some basics like jeans or sneakers."` — never returns `None`.

---

### `create_fit_card(outfit: str, new_item: dict) → str`

Calls the Groq LLM (`llama-3.3-70b-versatile`, temperature 0.9) to generate a short, casual Instagram-style caption grounded in the specific thrifted item and outfit.

- **outfit** (str): The outfit suggestion string returned by `suggest_outfit`.
- **new_item** (dict): The listing dict — used to include item name, price, and platform in the caption.
- **Returns**: A 1–3 sentence caption string. If `outfit` is empty or whitespace-only, returns `"[ERROR] Could not generate a fit card — outfit description was missing or incomplete."` — never raises an exception.

---

## How the Planning Loop Works

`run_agent(query, wardrobe)` in `agent.py` orchestrates the three tools in a conditional sequence — it never calls all three unconditionally.

1. **Parse the query.** The first sentence is extracted to isolate the item description from any wardrobe context the user included. Filler phrases ("I'm looking for", "find me") are stripped, as are size tokens (`size M`) and price tokens (`under $30`). Size and price are extracted separately into `session["parsed"]`.

2. **Call `search_listings`.** If the result is empty, `session["error"]` is set to a helpful message ("No listings found for '...'. Try a broader description or higher price limit.") and the session is returned immediately — `suggest_outfit` and `create_fit_card` are never called.

3. **Select the top result.** `session["selected_item"] = results[0]` (the highest-scoring listing).

4. **Call `suggest_outfit`.** The result is stored in `session["outfit_suggestion"]`. If the wardrobe is empty, `suggest_outfit` returns a fallback string — the loop proceeds to `create_fit_card` anyway, because a caption can still be generated from the item alone.

5. **Call `create_fit_card`.** The result is stored in `session["fit_card"]`.

6. **Return the session dict.** The caller checks `session["error"]` first; if `None`, all three output fields are populated.

---

## State Management

A single session dict is initialized at the start of each call and mutated as tools run. No tool re-prompts the user for data already in the session.

| Key | Set by | Used by |
|-----|--------|---------|
| `session["query"]` | User input | Planning loop |
| `session["parsed"]` | Planning loop (query parse) | `search_listings` call |
| `session["search_results"]` | `search_listings` result | Planning loop (selects top item) |
| `session["selected_item"]` | Planning loop (`search_results[0]`) | `suggest_outfit`, `create_fit_card` |
| `session["wardrobe"]` | User input | `suggest_outfit` |
| `session["outfit_suggestion"]` | `suggest_outfit` result | `create_fit_card` |
| `session["fit_card"]` | `create_fit_card` result | Final output |
| `session["error"]` | Any tool failure | Planning loop (early exit) |

`selected_item` flows directly from step 1 into steps 2 and 3 — the user never re-enters it.

---

## Error Handling

| Tool | Failure mode | Response | Concrete example from testing |
|------|-------------|----------|-------------------------------|
| `search_listings` | No results match the query | Sets `session["error"]`, returns session early without calling the remaining tools | Query `"designer ballgown size XXS under $5"` → `session["error"] = "No listings found for 'designer ballgown'. Try a broader description or higher price limit."` — `suggest_outfit` and `create_fit_card` were confirmed not called via mock assertions in `tests/test_agent.py` |
| `suggest_outfit` | `wardrobe["items"]` is empty | Returns fallback string; planning loop proceeds to `create_fit_card` | Passing `{"items": []}` returns `"Your wardrobe is empty — we can still show you the item..."` without raising. `create_fit_card` still ran and produced a caption — verified in `test_empty_wardrobe_still_runs_create_fit_card` |
| `create_fit_card` | `outfit` is empty or whitespace-only | Returns `"[ERROR] Could not generate a fit card — outfit description was missing or incomplete."` | Passing `""` and `"   "` both returned the error string without raising — verified in `test_create_fit_card_empty_outfit_returns_error` and `test_create_fit_card_whitespace_outfit_returns_error` |

---

## Spec Reflection

**One way the spec helped:**
The State Management table in `planning.md` made the planning loop straightforward to implement. Because every session key, its source, and its consumer were defined before writing code, `run_agent` could be written as a direct translation of the table — no guessing about what to store or when. The mock-based agent tests (`tests/test_agent.py`) were written against the same table and caught the correct behavior on the first run.

**One way implementation diverged from the spec:**
The spec described the query parser as simply extracting `description`, `size`, and `max_price` from the user's query. In practice, natural language queries like *"I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers."* caused the wardrobe context ("baggy jeans", "chunky sneakers") to pollute the description and change which listing ranked first. The parser was extended to split on sentence boundaries and use only the first sentence, which wasn't in the original spec. The spec also didn't account for bare numbers being misread as prices (e.g. `size 8` → `max_price=8.0`), so the price regex was tightened to require a `$` prefix.

---

## AI Usage

**Instance 1 — Implementing `search_listings`:**
I gave Claude the Tool 1 spec block from `planning.md` (inputs, return value, failure mode) and specified that it should use `load_listings()` from `utils/data_loader.py` rather than re-implementing file loading. Claude generated a filtering and scoring approach. I reviewed it and added one revision: the scoring function originally only matched against `title` and `description`, missing the `style_tags` list. I directed Claude to include `style_tags` in the text blob before scoring, which meaningfully improved relevance for style-based queries like "streetwear" or "y2k" that appear as tags rather than in the description text.

**Instance 2 — Writing the planning loop tests:**
I asked Claude to write pytest tests for `run_agent` that verified the three behaviors specified in `planning.md`: branching on `search_listings` result, session dict values being set correctly, and tools not being called unconditionally. Claude used `unittest.mock.patch` to isolate the loop from real LLM and data calls. I reviewed the output and added one test that wasn't in Claude's initial draft: `test_suggest_outfit_receives_selected_item`, which asserts that `suggest_outfit` is called with the actual item dict from session state rather than the raw query string. This caught a class of implementation error — passing the wrong argument type — that the other tests didn't cover.

---

## Bugs Found & Fixed

### Query parser polluted search description with wardrobe context

**What went wrong:**
Natural language queries like *"I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers."* were passed whole to `search_listings`. The full text — including "baggy jeans" and "chunky sneakers" — was scored against the listings index, boosting items that mentioned those wardrobe terms. This caused "Graphic Tee — 2003 Tour Bootleg Style" to outrank "Y2K Baby Tee — Butterfly Print" even though the shorter form query "vintage graphic tee under $30" returned the Y2K tee as the clear top result.

**What was changed (`agent.py`):**
- Parser now splits on sentence boundaries and uses only the first sentence for description extraction.
- Filler openers ("I'm looking for", "find me", "searching for") are stripped.
- Stop-words (`in`, `a`, `an`, `the`) are removed from the extracted description.
- Price regex tightened to require `$` prefix — previously `size 8` was misread as `max_price=8.0`.

**What was learned:**
Keyword scoring against a user's full natural language input causes unintended overlap between what they're searching for and the surrounding context they provide. Isolating the first sentence is a simple, transparent fix that avoids adding an extra LLM call to the parsing step.

---

### LLM output contained markdown formatting in plain-text panels

**What went wrong:**
The Groq LLM returns responses with markdown bold markers (`**Casual Day Outfit**`) by default. In Gradio's plain-text output boxes these render as literal asterisks rather than formatted text, producing output like `**Casual Summer Outfit**: Pair the tee...` visible to the user.

**What was changed (`tools.py`):**
Added a `_strip_markdown()` helper that removes `**bold**` and `*italic*` markers using regex. Applied to the return value of both `suggest_outfit` and `create_fit_card` before the string is stored in session state.

**What was learned:**
When LLM output goes into a plain-text UI panel, always strip markdown formatting — the model formats for readability by default and has no way to know the rendering context. Stripping at the tool boundary keeps the fix in one place regardless of how the output is later displayed.

---

## Project Structure

```
ai201-project2-fitfindr/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # load_listings(), get_example_wardrobe(), get_empty_wardrobe()
├── tests/
│   ├── test_tools.py          # 13 tests covering all three tools
│   └── test_agent.py          # 8 tests covering the planning loop
├── tools.py                   # search_listings, suggest_outfit, create_fit_card
├── agent.py                   # run_agent() — the planning loop
├── app.py                     # Gradio UI
└── planning.md                # Spec and design decisions
```
