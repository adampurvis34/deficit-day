# Scripts

## `macro_calc.py`

Sums a decomposed meal, validates it, and emits the Lose It! block.

```bash
python3 macro_calc.py meal.json
python3 macro_calc.py meal.json --json
cat meal.json | python3 macro_calc.py -
```

**Exit codes:** `0` clean · `1` macros failed the Atwater reconciliation · `2` bad input.

### Input schema

```jsonc
{
  "meal":    "Lunch",                      // Breakfast | Lunch | Dinner | Snacks
  "name":    "Chicken burrito bowl",       // what appears in Lose It!
  "context": "restaurant_fast_casual",     // drives the systematic skew, see below
  "components": [
    {
      "name":       "White rice",
      "state":      "cooked",              // optional, but say it for anything cooked
      "grams":      180,
      "confidence": "medium",              // high | medium | low
      "per100g":    {"kcal": 130, "protein": 2.7, "carbs": 28.2, "fat": 0.3}
    },
    {
      "name":       "Olive oil in the pan",
      "grams":      14,
      "confidence": "low",
      "hidden_fat": true,                  // marks this as an invisible-calorie line
      "per100g":    {"kcal": 884, "protein": 0, "carbs": 0, "fat": 100}
    },
    {
      "name":       "Protein bar",
      "confidence": "high",
      "totals":     {"kcal": 210, "protein": 20, "carbs": 24, "fat": 7}
    }
  ]
}
```

Each component gives **either** `grams` + `per100g`, **or** absolute `totals`. Use
`totals` when reading straight off a label or a restaurant's published data.

| Field | Effect |
|---|---|
| `confidence` | `high` ±5%, `medium` ±15%, `low` ±30% |
| `context` | `packaged` +0% · `home` +2% · `restaurant_fast_casual` +5% · `restaurant_casual` +12% · `restaurant_fine` +15% · `unknown` +8% |
| `hidden_fat: true` | Halves the systematic skew, since the invisible calories are now on the books |
| `alcohol_g` | Grams of ethanol, at 7 kcal/g. Keeps the Atwater check honest for drinks |
| `fiber_g` | Grams of fiber. Sits inside `carbs` but yields ~2 kcal/g not 4 — set it on vegetable- and legume-heavy components so the gate doesn't trip spuriously |

### How the range is computed

- **Random error**: component bands combined in quadrature —
  `σ = √Σ(kcalᵢ × bandᵢ)²`. Summing them instead would overstate the band badly,
  since the component errors are largely independent.
- **Systematic skew**: applied to the **high side only**. Food logging error is
  skewed toward underestimating, so a symmetric band misrepresents the risk.
- Result: `low = total − σ`, `high = total + σ + skew`.

### The Atwater gate

`protein×4 + carbs×4 + fat×9 + alcohol×7` must land within 8% of the summed calories.
Outside that, a mass or a density is wrong — the script says so, exits `1`, and
**withholds the Lose It! block** so there's nothing paste-ready to copy out of a broken
estimate.

---

## `usda_lookup.py`

Per-100 g macros from USDA FoodData Central, for foods the reference table doesn't cover.

```bash
export FDC_API_KEY=your_key      # free: https://fdc.nal.usda.gov/api-key-signup/
python3 usda_lookup.py "chicken thigh roasted"
python3 usda_lookup.py "greek yogurt" --datatype Branded --limit 10
```

Prefer `Foundation` and `SR Legacy` over `Branded` — branded rows are manufacturer-submitted
and noisier. The script flags any row whose own macros don't reconcile to its calories.

Rate limit is 1,000 requests/hour per IP. Stdlib only, no dependencies.

> **Note:** the response-parsing path has not been exercised against a live API response —
> it was written against the documented schema but the sandbox this was built in blocks
> `api.nal.usda.gov`. Run it once with a real key before relying on it; if the nutrient
> numbers come back empty, the field name to check is `nutrientNumber` vs `number` in
> `extract()`.
