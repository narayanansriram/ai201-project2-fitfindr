# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Searches the listings dataset for secondhand items that match the user's query, filtering by description keyword, clothing size, and maximum price. Returns all matching listings, or an empty list if none are found.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): A keyword or phrase describing the type of item to search for (e.g. "vintage graphic tee", "leather jacket").
- `size` (str): The clothing size to filter by (e.g. "S", "M", "XL"). Pass `None` to skip size filtering.
- `max_price` (float): The maximum price the user is willing to pay. Only listings at or below this value are returned.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of matching listing dictionaries. Each item contains: title (str), description (str), size (str), price (float), and category (str). If no matches are found, returns an empty list [].

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
The agent checks if the returned list is empty. If it is, it sets an error message in session state ("[ERROR] No listings found for your query.") and returns early — skipping suggest_outfit and create_fit_card. The user is informed and optionally asked to broaden their search (e.g., remove size or raise price limit).

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a specific thrifted item and the user's existing wardrobe, uses an LLM to suggest one or more complete outfit combinations that incorporate the new item.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The listing item selected from search_listings results — contains title, description, size, price, category.
- `wardrobe` (dict): The user's existing wardrobe, with a key "items" mapping to a list of clothing item strings (e.g., {"items": ["baggy jeans", "chunky sneakers", "white crop top"]}).

**What it returns:**
<!-- Describe the return value -->
A string describing one or more outfit combinations, e.g.: "Pair the vintage graphic tee with your baggy jeans and chunky sneakers for a relaxed streetwear look. Add a flannel overshirt if it's chilly."

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If wardrobe["items"] is empty or the LLM returns a blank response, the agent returns a fallback message: "Your wardrobe is empty — we can still show you the item, but can't suggest a full outfit. Try adding some basics like jeans or sneakers." It then proceeds to create_fit_card using only the new item.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Calls the LLM to generate a short, punchy, shareable outfit caption — the kind of thing someone would post on Instagram — based on the suggested outfit and the new item.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit description returned by suggest_outfit.
- `new_item` (dict): The listing item, used to ground the caption in the specific piece found.

**What it returns:**
<!-- Describe the return value -->
A string: a 1–3 sentence shareable caption, e.g.: "thrifted chaos, intentional vibes 🧢 vintage tee + baggy jeans + chunky sneakers = the look. found it for $18 and i'm never taking it off."

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If outfit is empty or the LLM returns nothing, the tool returns the error string: "[ERROR] Could not generate a fit card — outfit description was missing or incomplete." The agent surfaces this to the user without crashing.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The agent uses the following conditional logic:

Parse the user's query to extract description, size, and max_price. Call search_listings with these values.
Check results: If results == [], set session["error"] = "[ERROR] No listings found." and return early — do not call the remaining tools. Inform the user and suggest relaxing filters.
If results are found, set session["selected_item"] = results[0] (the best match).
Call suggest_outfit(session["selected_item"], session["wardrobe"]).
Check outfit: If the returned string is empty or a fallback message, set session["outfit_suggestion"] to that fallback and proceed anyway (fit card can still run with just the new item).
Set session["outfit_suggestion"] to the returned string.
Call create_fit_card(session["outfit_suggestion"], session["selected_item"]).
Set session["fit_card"] to the returned caption.
Return all three outputs to the user.

The loop is conditional — it only advances if the previous tool returned usable output. It never calls all three tools unconditionally.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

A single session dictionary is initialized at the start of each interaction and passed through each step:

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

No tool re-prompts the user for information already in session state. `selected_item` from step 1 flows directly into steps 2 and 3 without the user re-entering it.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets `session["error"]`, returns early, tells user: "No listings found for '[query]'. Try a broader description or higher price limit." |
| suggest_outfit | Wardrobe is empty (`wardrobe["items"] == []`) | Returns fallback string: "Your wardrobe is empty — showing the item only. Add items like jeans or sneakers for outfit suggestions." Proceeds to `create_fit_card`. |
| create_fit_card | `outfit` is empty or missing | Returns error string: "[ERROR] Could not generate a fit card — outfit description was missing." Displays error to user instead of crashing. |

---

## Architecture

```
User query
    │
    ▼
Planning Loop ────────────────────────────────────────────────────┐
    │                                                             │
    ├─► search_listings(description, size, max_price)            │
    │       │                                                     │
    │       ├─ results == [] ──► [ERROR] "No listings found      │
    │       │                    for '[query]'. Try broader       │
    │       │                    description or higher price." ───┤
    │       │                                                     │
    │       └─ results = [item, ...]                              │
    │               │                                             │
    │           session["selected_item"] = results[0]            │
    │               │                                             │
    ├─► suggest_outfit(selected_item, wardrobe)                  │
    │       │                                                     │
    │       ├─ wardrobe empty ──► fallback: "Wardrobe is empty   │
    │       │                    — showing item only."            │
    │       │                               │                     │
    │       └─ outfit returned              │                     │
    │               │◄───────────────────────                     │
    │           session["outfit_suggestion"] = result            │
    │               │                                             │
    └─► create_fit_card(outfit_suggestion, selected_item)        │
            │                                                     │
            ├─ outfit missing ──► [ERROR] "Could not generate    │
            │                    fit card — outfit missing." ─────┘
            │
            └─ success
                    │
                session["fit_card"] = caption
                    │
                    ▼
            Return to user:
            selected_item + outfit_suggestion + fit_card
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**search_listings:**
I'll give Claude the Tool 1 spec block from planning.md (what it does, all three
input parameters with types, return value, and failure mode) along with the note
that it should use `load_listings()` from `utils/data_loader.py` — not re-implement
file loading. I'll ask it to generate the function body in `tools.py` only.

Before running it, I'll check that the generated code:
- Filters by all three parameters (and skips size filtering when `size=None`)
- Returns a list of dicts, not a string or other type
- Returns `[]` on no match rather than raising an exception

I'll then test it with 3 queries:
1. A normal match ("vintage graphic tee", size=None, max_price=50) — expect results
2. An impossible query ("designer ballgown", size="XXS", max_price=5) — expect `[]`
3. A price boundary case ("jacket", size=None, max_price=10) — verify all returned
   items have price ≤ 10

---

**suggest_outfit:**
I'll give Claude the Tool 2 spec block plus the detail that it calls Groq's
`llama-3.3-70b-versatile` using `GROQ_API_KEY` from `.env`. I'll ask it to write
the function and handle the empty wardrobe case explicitly.

Before running it, I'll check that:
- The LLM prompt includes both `new_item` details and `wardrobe["items"]`
- The function doesn't crash when `wardrobe["items"]` is `[]`
- It returns a string in all cases (never `None`)

I'll test with 3 inputs:
1. A real item + a populated wardrobe — expect a natural outfit suggestion
2. A real item + an empty wardrobe (`{"items": []}`) — expect the fallback message,
   no exception
3. A very minimal wardrobe (one item) — expect a suggestion that only references
   what's available

---

**create_fit_card:**
I'll give Claude the Tool 3 spec block and specify that the function takes both
`outfit` (str) and `new_item` (dict), calls the LLM, and must produce varied output
across runs. I'll ask it to set a higher temperature (0.9+) to ensure variation.

Before running it, I'll check that:
- The function signature matches `create_fit_card(outfit, new_item)` exactly
- It guards against an empty `outfit` string and returns an error string rather
  than crashing
- The LLM prompt references both the outfit description and the specific item found

I'll test with 3 cases:
1. A full outfit string + item dict — run 3 times and confirm outputs differ
2. An empty `outfit` string (`""`) — expect the error string, no exception
3. A minimal outfit (one sentence) — confirm the caption still sounds shareable,
   not like a product description

---

**Milestone 4 — Planning loop and state management:**
I'll give Claude three things as input: the Planning Loop section, the State
Management table, and the architecture diagram from planning.md. I'll ask it to implement `run_agent(query, wardrobe)` in `agent.py` — not in `tools.py`.

Before running it, I'll check that:
- The loop stops after `search_listings` if results are empty and does not call the remaining two tools
- `selected_item` is pulled from session state in step 2, not re-parsed from the query
- All three session keys (`selected_item`, `outfit_suggestion`, `fit_card`) are set in the right order
- The function returns the full session dict (or a structured response), not just the fit card

I'll verify correct behavior with 4 test runs:
1. Valid query + populated wardrobe — all 3 tools run, all 3 outputs populated
2. Impossible query — loop exits after `search_listings`, user sees error message, `suggest_outfit` and `create_fit_card` are never called
3. Valid query + empty wardrobe — `suggest_outfit` returns fallback, `create_fit_card` still runs and produces a caption
4. Two back-to-back queries in the same session — confirm state from query 1 doesn't bleed into query 2

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1: Parse the query and call `search_listings`**
<!-- What does the agent do first? Which tool is called? With what input? -->

The planning loop extracts three values from the user's query:
- `description = "vintage graphic tee"`
- `size = None` (no size mentioned)
- `max_price = 30.0`

It calls:
`search_listings(description="vintage graphic tee", size=None, max_price=30.0)`

The tool scans the mock listings dataset for items whose description contains
"vintage" or "graphic tee" and whose price is ≤ 30.0. It returns:

```python
[
  {"title": "Faded Band Tee", "description": "vintage graphic band tee, slightly
   oversized", "size": "M", "price": 18.00, "category": "tops"},
  {"title": "90s Skate Tee", "description": "vintage graphic skate tee, boxy fit",
   "size": "L", "price": 25.00, "category": "tops"}
]
```

The planning loop checks: `results != []` → proceed.
Sets `session["selected_item"] = results[0]` (the Faded Band Tee at $18).

---

**Step 2: Call `suggest_outfit`**
<!-- What happens next? What was returned from step 1? What tool is called now? -->

The planning loop calls:
`suggest_outfit(new_item=session["selected_item"], wardrobe={"items": ["baggy jeans",
"chunky sneakers"]})`

The tool builds a prompt: *"The user just found a 'Faded Band Tee' — a vintage
graphic band tee, slightly oversized. Their current wardrobe includes: baggy jeans,
chunky sneakers. Suggest one complete outfit using the new item and pieces from
their wardrobe."*

The LLM returns:
`"Wear the faded band tee slightly tucked into your baggy jeans, cuffed once at
the ankle. Finish with your chunky sneakers. The oversized fit of the tee balances
the volume of the jeans without looking sloppy."`

The planning loop checks: response is non-empty → proceed.
Sets `session["outfit_suggestion"]` to the returned string.

---

**Step 3: Call `create_fit_card`**
<!-- Continue until the full interaction is complete -->

The planning loop calls:
`create_fit_card(outfit=session["outfit_suggestion"],
new_item=session["selected_item"])`

The tool builds a prompt: *"Write a short, punchy Instagram caption for this outfit:
[outfit_suggestion]. The new thrifted piece is a Faded Band Tee, found for $18.
Make it sound like something worth sharing — not a product description."*

The LLM returns:
`"$18 and it goes with literally everything 🤝 vintage band tee + baggy jeans +
chunky sneakers. thrift math just hits different."`

Sets `session["fit_card"]` to the returned caption.

---

**Final output to user:**
<!-- What does the user actually see at the end? -->

```
🛍  Found: "Faded Band Tee" — Size M — $18.00
    "vintage graphic band tee, slightly oversized"

👗  How to wear it:
    Wear the faded band tee slightly tucked into your baggy jeans, cuffed once
    at the ankle. Finish with your chunky sneakers. The oversized fit of the tee
    balances the volume of the jeans without looking sloppy.

✨  Fit card:
    $18 and it goes with literally everything 🤝 vintage band tee + baggy jeans
    + chunky sneakers. thrift math just hits different.
```
