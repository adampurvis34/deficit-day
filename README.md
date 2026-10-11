# deficit-day

Tools for tracking a calorie deficit without it becoming a chore.

## `skills/food-macros`

Snap a photo of a meal — or just describe it — and get calories and macros accurate
enough to log, plus a block that pastes straight into Lose It!.

### Install

```bash
git clone https://github.com/adampurvis34/deficit-day.git
mkdir -p ~/.claude/skills
cp -r deficit-day/skills/food-macros ~/.claude/skills/
```

Then start a new Claude session and send it a photo of your lunch. The skill triggers on
food photos, meal descriptions, "what are the macros", and "log this".

Optional, for foods outside the built-in reference table:

```bash
export FDC_API_KEY=your_key    # free: https://fdc.nal.usda.gov/api-key-signup/
```

### What it does

```
  Chicken burrito bowl (Chipotle)  —  Lunch
  ─────────────────────────────────────────────────────────────────────
  Component                              g   kcal     P     C     F  conf
  ───────────────────────────────────────────────────────────────────────
  White rice (cooked)                  180    234   4.9  50.8   0.5  medium
  Black beans (cooked)                  90    119   8.0  21.3   0.5  medium
  Chicken (thigh, grilled) (cooked)    120    251  31.2   0.0  13.1  medium
  Fajita vegetables (cooked)            60     26   0.8   6.1   0.1  low
  Pico de gallo                         60     22   0.9   4.2   0.1  medium
  Shredded cheddar                      30    121   7.5   0.4   9.9  medium
  Guacamole                             60     93   1.2   5.2   8.1  medium
  ───────────────────────────────────────────────────────────────────────
  TOTAL                                600    866  54.5  88.0  32.3

  Atwater check: OK  (macros imply 861 kcal vs 866 stated, -0.5%)

  Estimate: 865 kcal   (range 805–970)
  Uncertainty driven by: Chicken (±38), White rice (±35), Cheddar (±18)

  LOSE IT! — QUICK ADD
  Meal:     Lunch          Calories: 865
  Protein:  54 g           Carbs: 88 g      Fat: 32 g
```

Chipotle's own published figure for that build is ~905 kcal — inside the band.

### Why it's more accurate than asking an AI "how many calories is this"

Asked cold, a vision model runs about **40% mean error** on calories from a photo. Given
the *mass* of each component, the same model drops to about **29%** — mass is the single
highest-leverage input, more valuable than the ingredient list or any prompting trick.

So the skill never estimates calories directly. It:

1. **Decomposes** the meal into single-density components
2. **Finds a scale reference** in the frame — cutlery, plate rim, a can, a hand
3. **Estimates grams** per component, with a stated confidence band
4. **Applies nutrient density** from a USDA-grounded table
5. **Adds what the photo can't show** — cooking oil, dressing, sauce. This is where
   400-600 kcal/day typically goes missing
6. **Validates** with an Atwater check and reports an honest range

Full citations in [`references/research-basis.md`](skills/food-macros/references/research-basis.md).

### Layout

```
skills/food-macros/
├── SKILL.md                      the six-step protocol
├── references/
│   ├── portion-anchors.md        scale references, densities, cooked↔raw factors
│   ├── nutrient-density.md       per-100 g macros, ~150 foods, USDA-grounded
│   ├── hidden-calories.md        cooking fat, dressings, restaurant adjustments
│   ├── loseit-integration.md     Quick Add, custom foods, the unofficial MCP server
│   └── research-basis.md         why it's built this way, with sources
├── scripts/
│   ├── macro_calc.py             totals, Atwater gate, uncertainty, paste block
│   ├── usda_lookup.py            FoodData Central lookup for anything not in the table
│   └── README.md                 input schema
└── examples/
    └── chipotle-bowl.json
```

### Honest limitations

- **~15-25% error on mixed restaurant dishes** even done well. Better than the ~40% of a
  naive ask, not as good as a kitchen scale. Ranges are reported for a reason.
- **Stacked or obscured food** can't be massed from one angle. The skill asks for a
  second photo rather than guessing.
- **Consistency beats per-meal precision.** The same method applied daily gives a trend
  that's right even on days the absolute number isn't.
- **`usda_lookup.py`'s response parsing is unverified against a live API** — it was
  written to the documented schema, but the sandbox it was built in blocks
  `api.nal.usda.gov`. Run it once with a real key before relying on it.

## `apps/hockey-card-vault`

A separate tool: a Claude artifact that identifies hockey cards from photos and tracks the
collection's value in CAD over time. See [its README](apps/hockey-card-vault/README.md).

## Related

Pairs with the `calorie-deficit-tracker` skill, which handles the burn side. This one
produces the intake number that one consumes.
