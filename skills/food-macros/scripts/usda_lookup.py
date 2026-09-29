#!/usr/bin/env python3
"""
usda_lookup.py — pull per-100 g macros from USDA FoodData Central.

The reference table in references/nutrient-density.md covers most foods. Use this when a
food isn't in it, or when you want to confirm a value against the primary source.

Setup:
    Get a free key at https://fdc.nal.usda.gov/api-key-signup/
    export FDC_API_KEY=your_key_here

Usage:
    python3 usda_lookup.py "chicken thigh roasted"
    python3 usda_lookup.py "greek yogurt" --datatype Branded --limit 10
    python3 usda_lookup.py "quinoa cooked" --json

Data types, best-first for accuracy:
    Foundation  — lab-analyzed whole foods, highest quality
    SR Legacy   — the classic Standard Reference tables, broad coverage
    Survey      — FNDDS, what people actually eat, good for mixed dishes
    Branded     — manufacturer-submitted labels, widest but noisiest

Only stdlib, no dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.nal.usda.gov/fdc/v1/foods/search"

# FoodData Central nutrient numbers.
WANTED = {
    "208": "kcal",      # Energy, kcal
    "203": "protein",
    "205": "carbs",     # Carbohydrate, by difference
    "204": "fat",       # Total lipid
    "291": "fiber",
    "269": "sugars",
}


def search(query, api_key, datatype=None, limit=5, timeout=30):
    params = {"api_key": api_key, "query": query, "pageSize": str(limit)}
    if datatype:
        params["dataType"] = datatype
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract(food):
    """Pull the nutrients we care about out of one search hit."""
    out = {v: None for v in WANTED.values()}
    for n in food.get("foodNutrients") or []:
        # The search endpoint uses 'nutrientNumber'; some responses use 'number'.
        num = str(n.get("nutrientNumber") or n.get("number") or "")
        if num in WANTED:
            value = n.get("value")
            if value is not None:
                out[WANTED[num]] = value
    return {
        "fdcId": food.get("fdcId"),
        "description": food.get("description"),
        "dataType": food.get("dataType"),
        "brand": food.get("brandOwner"),
        # Search results are normalized per 100 g for non-branded types.
        "per100g": out,
    }


def atwater_ok(per100g, tolerance=0.10):
    """Does this row's own macro/calorie arithmetic hold up?"""
    kcal = per100g.get("kcal")
    p, c, f = per100g.get("protein"), per100g.get("carbs"), per100g.get("fat")
    if not kcal or None in (p, c, f):
        return None
    implied = p * 4 + c * 4 + f * 9
    return abs(implied - kcal) / kcal <= tolerance


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("query", help="food to search for")
    ap.add_argument(
        "--datatype",
        choices=["Foundation", "SR Legacy", "Survey (FNDDS)", "Branded"],
        help="restrict to one FDC data type",
    )
    ap.add_argument("--limit", type=int, default=5, help="results to show (default 5)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    api_key = os.environ.get("FDC_API_KEY")
    if not api_key:
        print(
            "error: FDC_API_KEY is not set.\n"
            "  Get a free key: https://fdc.nal.usda.gov/api-key-signup/\n"
            "  Then: export FDC_API_KEY=your_key_here",
            file=sys.stderr,
        )
        return 2

    try:
        data = search(args.query, api_key, args.datatype, args.limit)
    except urllib.error.HTTPError as exc:
        detail = "invalid or rate-limited API key" if exc.code in (401, 403, 429) else ""
        print(f"error: FoodData Central returned HTTP {exc.code} {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"error: could not reach FoodData Central: {exc.reason}", file=sys.stderr)
        return 1

    foods = [extract(f) for f in data.get("foods", [])]
    if not foods:
        print(f"No matches for {args.query!r}.", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(foods, indent=2))
        return 0

    print(f"\n  USDA FoodData Central — {args.query!r}  (per 100 g)\n")
    for f in foods:
        n = f["per100g"]
        desc = f["description"] or "?"
        print(f"  {desc[:62]}")
        meta = f"    [{f['dataType']}] fdcId={f['fdcId']}"
        if f["brand"]:
            meta += f"  brand={f['brand'][:28]}"
        print(meta)

        def g(key):
            v = n.get(key)
            return f"{v:g}" if v is not None else "?"

        print(
            f"    {g('kcal')} kcal  |  P {g('protein')}  C {g('carbs')}  "
            f"F {g('fat')}  |  fiber {g('fiber')}  sugar {g('sugars')}"
        )
        ok = atwater_ok(n)
        if ok is False:
            print("    ^ warning: this row's macros do not reconcile to its calories")
        print()

    print("  Copy the per-100 g figures into your meal JSON as 'per100g'.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
