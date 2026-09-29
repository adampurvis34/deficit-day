---
name: food-macros
description: Estimate calories and macros from a food photo or a written description, then produce a block Adam can paste straight into Lose It!. Use whenever he sends a picture of a meal, describes what he ate, asks "what are the macros", "how many calories is this", "log this", or wants a meal broken down before logging. Also use for menu items, recipes, and packaged foods.
---

# Food → Macros → Lose It!

Turn a photo or description of food into calories and macros that are accurate enough to log,
then hand back a paste-ready block for Lose It!.

## The one rule that drives accuracy

**Never estimate calories directly. Estimate mass, then multiply by nutrient density.**

Vision models asked "how many calories is this?" run about 40% mean error. The same models
given the mass of each component drop to roughly 29%, and mass is the single most valuable
cue — more than knowing the ingredient list, more than the cuisine, more than chain-of-thought
prompting. See `references/research-basis.md` for the citations.

So the whole protocol is built around getting grams right, and treating kcal as a derived
number, never an observed one.

## Protocol

### Step 1 — Decompose

Break the meal into components that each have a single nutrient density. Do not carry
"chicken burrito bowl" as one item. Carry rice, beans, chicken, cheese, guac, salsa.

Separate anything cooked in or coated with fat from the fat itself when the amount is
material. "Sautéed spinach" is spinach + oil, and the oil is usually 80% of the calories.

### Step 2 — Find the scale reference

Before estimating any mass, name what in the frame gives you scale. In priority order:

1. A packaged item with a known size (can, bottle, wrapper, carton)
2. Cutlery — a dinner fork is ~18-19 cm, a teaspoon ~15 cm
3. The plate or bowl rim — home dinner plate 26-27 cm, restaurant plate 28-30 cm,
   side plate 18-20 cm
4. A hand in frame
5. Nothing → say so, and widen the uncertainty band

Load `references/portion-anchors.md` for the full table of reference objects, typical
serving weights, and the volume→mass densities.

**Adam is 6'4". His palm and cupped hand are roughly 25-30% larger than the generic
hand-portion charts assume.** A "palm of chicken" for him is ~130-150 g cooked, not the
85-110 g in standard guides. Use the adjusted figures in the reference file, not the
generic ones.

### Step 3 — Estimate mass per component

Give each component a gram figure and a confidence tag:

| Tag | Means | Band |
|---|---|---|
| `high` | Weighed, or read off a label/menu with nutrition data | ±5% |
| `medium` | Standard portion, packaged item, home cooking you can size confidently | ±15% |
| `low` | Restaurant plate, mixed dish, unknown prep, obscured food | ±30% |

State the reasoning in one clause — "rice fills ~⅓ of a 27 cm plate at ~2 cm deep ≈ 180 g".
Do not skip this. The written reasoning is what keeps the estimate honest.

Watch the state of the food. Databases list some foods raw and some cooked, and the
difference is large: 100 g raw chicken is ~73 g cooked; 100 g dry rice is ~280 g cooked;
100 g dry pasta is ~225 g cooked. Always say which state your gram figure is in and match
it to the density you use.

### Step 4 — Apply nutrient density

Use `references/nutrient-density.md` for per-100 g values. Prefer, in order:

1. The actual label or the restaurant's published nutrition data
2. The reference table in this skill
3. A USDA FoodData Central lookup (`scripts/usda_lookup.py`, needs a free API key)
4. Your own estimate — and drop confidence to `low` if it comes to this

### Step 5 — Add what the photo does not show

This is where most logging goes wrong. The average tracked day underestimates intake by
400-600 kcal, and roughly half of that is cooking fat, sauces, dressings and drinks that
never appear as a distinct object in the picture.

Load `references/hidden-calories.md` and walk the checklist. The short version:

- Anything seared, sautéed, fried, roasted or "glazed" carries added fat you cannot see.
  Home cooking: ~1 tbsp per pan. Restaurant: 2-4 tbsp per dish.
- Dressed salads are mostly dressing calories.
- Restaurant food runs meaningfully above what the same dish looks like it should be.
- Drinks, and anything eaten standing up next to the meal, get forgotten.

If the prep is unknown and the dish plausibly involves added fat, add the fat with a
`low` confidence tag rather than omitting it. Omitting is a guaranteed underestimate;
including it with a wide band is an honest one.

### Step 6 — Compute, validate, report

Run the calculator rather than doing the arithmetic in your head:

```bash
python3 scripts/macro_calc.py meal.json
```

It sums components, runs an Atwater reconciliation, computes an asymmetric uncertainty
range, and emits the Lose It! paste block. See `scripts/README.md` for the input schema.
Build the JSON from your Step 1-5 work and pass it in.

The Atwater check is a real gate: `(protein × 4) + (carbs × 4) + (fat × 9)` must land
within ~8% of the calorie figure. If it does not, a macro or a mass is wrong — go back
and find it before reporting. The script fails loudly and withholds the paste block when
it does not reconcile, so a broken estimate can never be copied out by accident.

Two legitimate exceptions the script handles once you tell it about them: **alcohol**
(7 kcal/g, not a macro — set `alcohol_g`) and **fiber** on vegetable- or legume-heavy
meals (sits inside carbs but yields ~2 kcal/g, not 4 — set `fiber_g`, values in
`references/nutrient-density.md`).

## What to report

Lead with the number, then the working, then the paste block.

1. **Headline**: calories as a range, plus the point estimate to log. `~720 kcal (640-830)`
2. **Table**: component, grams, kcal, P/C/F, confidence
3. **The one question worth asking** — if a single unknown moves the total by more than
   ~15%, ask it. Ask *one*, not five. Usually it is "was this cooked in oil or butter, and
   roughly how much?" or "is that a 6 oz or a 10 oz portion?"
4. **Paste block** for Lose It!

Report a range. Adam's `calorie-deficit-tracker` skill already works in ranges and this
feeds it directly — false precision here corrupts the deficit number downstream.

## Lose It! output

Default to the **Quick Add** format — one line, no database search, macros included:

```
LOSE IT! — QUICK ADD
Meal:     Dinner
Name:     Chicken burrito bowl (Chipotle)
Calories: 720
Protein:  52 g
Carbs:    68 g
Fat:      26 g
```

Offer the per-component breakdown as well when the meal is likely to repeat — logging
components against real database entries is more accurate over time and makes the meal
re-loggable in two taps.

`references/loseit-integration.md` covers the three ways in (Quick Add, custom food,
per-component), and the unofficial MCP server that can write to Lose It! directly and
skip the copy-paste entirely.

## Honesty rules

- Never report a single hard number for a mixed or restaurant dish.
- Never silently drop a component because you cannot identify it — name it and flag it.
- If the photo is too dark, too oblique, or the food is stacked/obscured so mass cannot be
  judged, say so and ask for a second angle rather than guessing.
- Say which components dominate the uncertainty. "The ±90 kcal is almost entirely the
  dressing" is more useful than a bare range.
- These are estimates for logging, not clinical measurement. Consistency of method matters
  more than any single meal's accuracy — the same method applied daily gives a trend that
  is right even when individual days are off.
