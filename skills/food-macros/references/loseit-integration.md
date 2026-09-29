# Getting numbers into Lose It!

Three ways in, from least to most automated. Also: what I found when I went looking for
an official API or MCP server.

---

## 1. Quick Add — the default

Fastest path. No database search, no food matching, macros included.

**In the app:** the `+` on a meal → **Quick Add** (called *Add Calories* on some builds).
Enter calories, then expand nutrients to add protein, carbs and fat.

This is what `macro_calc.py` emits by default:

```
LOSE IT! — QUICK ADD
Meal:     Lunch
Name:     Chicken burrito bowl (Chipotle)
Calories: 865
Protein:  54 g
Carbs:    88 g
Fat:      32 g
```

Four fields, four taps. Best for one-off meals and anything from a restaurant.

**Limitation:** Quick Add entries don't join the food database, so they can't be
re-logged as a unit later. For a meal that repeats, use a custom food instead.

---

## 2. Custom food — for meals that repeat

**Profile → Foods → Create a Food** (or *Create Food* at the top of any meal screen).

Enter name, serving size, calories, fat, carbs, protein. It's then searchable forever and
re-logs in two taps.

Worth the extra 60 seconds for anything eaten weekly — a standard breakfast, a meal-prep
container, a regular order. Set the serving size to the actual portion (e.g. "1 bowl")
rather than 100 g, so future logging needs no arithmetic.

**Custom recipes** (Profile → Recipes → Create Recipe) are better still for home cooking:
enter the ingredients once with total servings, and Lose It! computes per-serving macros.
Cook a batch of five, log one-fifth. Recipe *import* from a URL is Premium; building one
by hand is free.

---

## 3. Direct write via the unofficial MCP server

**Lose It! has no public API and no official MCP server.** I checked — there's no
developer portal, no OAuth app registration, and no published endpoints. The only
first-party integration surface is Validic, a healthcare data-aggregation vendor that
resells access to enterprise customers; that's not something an individual can use.

What does exist is community-built and works by talking to the private endpoints that
Lose It!'s own web app uses.

### `cabird/loseit-mcp` — the one that can write

<https://github.com/cabird/loseit-mcp> · Python · 0BSD

Nine tools, and critically it can **write** to the diary:

| Tool | |
|---|---|
| `log_custom_food` | **logs arbitrary calories and macros** — exactly the Quick Add above, automated |
| `log_food` | logs a database food to a meal |
| `search_food` / `describe_food` | database lookup |
| `get_diary` | a day's entries with totals |
| `log_weight` / `get_weight_history` | weigh-ins |
| `delete_entry` | remove an entry |
| `whoami` | account check |

Auth is `LOSEIT_EMAIL` + `LOSEIT_PASSWORD` (or a `LOSEIT_TOKEN` JWT), with the session
cached at `~/.config/loseit-mcp/session.json`. It speaks Lose It!'s private GWT-RPC
endpoint via the `phitoduck/lose-it` SDK.

**With this installed, the copy-paste step disappears entirely** — this skill's output
becomes a `log_custom_food` call and the meal lands in the diary directly.

### `the-mace/loseit-mcp-local` — read-only, more robust

<https://github.com/the-mace/loseit-mcp-local> · Python · MIT

A different design: Playwright scrapes your own account daily into a local SQLite file,
and the MCP server reads only from that. Four read tools (`get_daily_summary`,
`get_food_log`, `get_weight_history`, `get_water_log`). It never writes to Lose It! and
never talks to their servers at query time.

Useless for logging, but good for "what did I actually eat this week" analysis, and it
degrades gracefully — a broken scrape means stale data, not a failed write.

### Before you install either one

Be clear-eyed about the trade:

- **Unofficial and unsupported.** Both depend on private endpoints or DOM structure.
  A Lose It! web release can break them without warning.
- **Full account credentials.** `cabird/loseit-mcp` wants your Lose It! email and
  password in an environment variable, and caches a session token on disk. That's your
  real account, not a scoped token you can revoke independently. Use a unique password.
- **Plausibly against their terms of service.** Automating a private API is the kind of
  thing consumer app ToS generally prohibit. The realistic risk to a single personal
  account is low, but it isn't zero and it's your account.
- **Neither is widely used.** Single-digit stars. Read the source before trusting it
  with credentials — both are small enough to actually read in a sitting.

**Recommendation:** start with Quick Add. It's four taps and it always works. Only add the
MCP server if the copy-paste genuinely becomes the thing that stops you logging — that's
a real failure mode, and at that point the trade is worth it. If you do install it,
`cabird/loseit-mcp` is the right one, and read `loseit_client.py` first.

---

## What about exporting?

Lose It! Premium exports the food log to CSV, which is useful for analysis but not for
input. There's no documented CSV *import* format for bulk-adding entries, so bulk backfill
isn't available through supported channels either.
