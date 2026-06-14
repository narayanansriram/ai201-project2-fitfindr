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
Searches listings dataset based on input parameters and returns items that match the parameters that are passed in. 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ...
- `size` (str): ...
- `max_price` (float): ...

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
- `outfit` (...): ...

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
| `session["selected_item"]` | `search_listings` result | `suggest_outfit`, `create_fit_card` |
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

```mermaid
flowchart TD
    A[User Query] --> B[Planning Loop]
    B --> C[search_listings\ndescription, size, max_price]
    C -->|results == []| D[ERROR: No listings found\nReturn early to user]
    C -->|results found| E[session: selected_item = results 0]
    E --> F[suggest_outfit\nselected_item, wardrobe]
    F -->|wardrobe empty| G[Fallback: item-only suggestion]
    G --> H[session: outfit_suggestion = result]
    F -->|outfit returned| H
    H --> I[create_fit_card\noutfit_suggestion, selected_item]
    I -->|outfit missing| J[ERROR: Fit card failed\nReturn error string to user]
    I -->|success| K[session: fit_card = caption]
    K --> L[Return to user:\nselected_item + outfit_suggestion + fit_card]

    B -.reads/writes.-> M[(session state)]
    C -.reads/writes.-> M
    F -.reads/writes.-> M
    I -.reads/writes.-> M
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

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->

**Step 3:**
<!-- Continue until the full interaction is complete -->

**Final output to user:**
<!-- What does the user actually see at the end? -->
