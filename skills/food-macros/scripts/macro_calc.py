#!/usr/bin/env python3
"""
macro_calc.py — turn a decomposed meal into validated macros and a Lose It! paste block.

Usage:
    python3 macro_calc.py meal.json
    python3 macro_calc.py meal.json --json      # machine-readable output
    cat meal.json | python3 macro_calc.py -

Input schema is documented in scripts/README.md. The short version: a meal has a list of
components, and each component gives either `grams` + `per100g` densities, or absolute
`totals`. Every component carries a confidence tag that drives the uncertainty band.
"""

from __future__ import annotations

import argparse
import json
import math
import sys

# Relative uncertainty band by confidence tag.
BANDS = {"high": 0.05, "medium": 0.15, "low": 0.30}

# Upward skew applied to the high end of the range, by eating context. The error
# distribution for food logging is skewed toward underestimating, so the band is
# asymmetric. See references/hidden-calories.md.
CONTEXT_BIAS = {
    "packaged": 0.00,
    "home": 0.02,
    "restaurant_fast_casual": 0.05,
    "restaurant_casual": 0.12,
    "restaurant_fine": 0.15,
    "unknown": 0.08,
}

ATWATER_TOLERANCE = 0.08  # 8% — allows for fiber and rounding residuals
MACROS = ("protein", "carbs", "fat")


class MealError(Exception):
    """Input that cannot be reconciled into a meal."""


def _num(value, field, where):
    if value is None:
        return 0.0
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MealError(f"{where}: '{field}' must be a number, got {value!r}")
    if value < 0:
        raise MealError(f"{where}: '{field}' must not be negative, got {value}")
    if math.isnan(value) or math.isinf(value):
        raise MealError(f"{where}: '{field}' must be finite, got {value}")
    return float(value)


def resolve_component(raw, index):
    """Normalize one component into absolute kcal and macro grams."""
    where = f"component[{index}]"
    if not isinstance(raw, dict):
        raise MealError(f"{where}: expected an object, got {type(raw).__name__}")

    name = raw.get("name") or f"item {index + 1}"
    where = f"component[{index}] ({name})"

    confidence = str(raw.get("confidence", "medium")).lower()
    if confidence not in BANDS:
        raise MealError(
            f"{where}: confidence must be one of {sorted(BANDS)}, got {confidence!r}"
        )

    grams = _num(raw.get("grams"), "grams", where) if "grams" in raw else None
    alcohol_g = _num(raw.get("alcohol_g"), "alcohol_g", where)
    fiber_g = _num(raw.get("fiber_g"), "fiber_g", where)

    if "totals" in raw:
        totals = raw["totals"]
        if not isinstance(totals, dict):
            raise MealError(f"{where}: 'totals' must be an object")
        kcal = _num(totals.get("kcal"), "totals.kcal", where)
        macros = {m: _num(totals.get(m), f"totals.{m}", where) for m in MACROS}
    elif "per100g" in raw:
        if grams is None:
            raise MealError(f"{where}: 'per100g' requires 'grams'")
        density = raw["per100g"]
        if not isinstance(density, dict):
            raise MealError(f"{where}: 'per100g' must be an object")
        scale = grams / 100.0
        kcal = _num(density.get("kcal"), "per100g.kcal", where) * scale
        macros = {
            m: _num(density.get(m), f"per100g.{m}", where) * scale for m in MACROS
        }
    else:
        raise MealError(f"{where}: needs either 'per100g' + 'grams', or 'totals'")

    return {
        "name": name,
        "grams": grams,
        "state": raw.get("state"),
        "note": raw.get("note"),
        "confidence": confidence,
        "hidden_fat": bool(raw.get("hidden_fat", False)),
        "kcal": kcal,
        "alcohol_g": alcohol_g,
        "fiber_g": fiber_g,
        **macros,
    }


def atwater(protein, carbs, fat, alcohol=0.0, fiber=0.0):
    """Calories implied by the macros, using general Atwater factors.

    Fiber is included in 'carbs by difference' (how USDA and food labels report it)
    and general Atwater charges it the full 4 kcal/g, but it actually yields closer to
    2. Passing fiber applies that correction. It matters for vegetable-heavy meals,
    where the uncorrected figure can overstate calories by 20%+.
    """
    return protein * 4 + carbs * 4 + fat * 9 + alcohol * 7 - fiber * 2


def analyze(meal):
    if not isinstance(meal, dict):
        raise MealError("top level must be a JSON object")

    raw_components = meal.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise MealError("'components' must be a non-empty list")

    components = [resolve_component(c, i) for i, c in enumerate(raw_components)]

    total_kcal = sum(c["kcal"] for c in components)
    totals = {m: sum(c[m] for c in components) for m in MACROS}
    total_alcohol = sum(c["alcohol_g"] for c in components)
    total_fiber = sum(c["fiber_g"] for c in components)
    total_grams = sum(c["grams"] for c in components if c["grams"] is not None)

    # --- Atwater reconciliation -------------------------------------------------
    implied = atwater(
        totals["protein"], totals["carbs"], totals["fat"], total_alcohol, total_fiber
    )
    if total_kcal > 0:
        drift = (implied - total_kcal) / total_kcal
    else:
        drift = 0.0
    reconciles = abs(drift) <= ATWATER_TOLERANCE

    # --- Uncertainty ------------------------------------------------------------
    # Random error: component bands combined in quadrature, since the errors are
    # largely independent. Summing them would overstate the band badly.
    variance = sum((c["kcal"] * BANDS[c["confidence"]]) ** 2 for c in components)
    sigma = math.sqrt(variance)

    context = str(meal.get("context", "unknown")).lower()
    if context not in CONTEXT_BIAS:
        raise MealError(
            f"context must be one of {sorted(CONTEXT_BIAS)}, got {context!r}"
        )
    bias_rate = CONTEXT_BIAS[context]
    # If hidden fat has already been entered explicitly, the systematic skew is
    # half accounted for — don't charge for it twice.
    if any(c["hidden_fat"] for c in components):
        bias_rate /= 2
    bias = total_kcal * bias_rate

    low = max(0.0, total_kcal - sigma)
    high = total_kcal + sigma + bias

    # Which components dominate the uncertainty?
    contributions = sorted(
        (
            {
                "name": c["name"],
                "kcal_sigma": c["kcal"] * BANDS[c["confidence"]],
                "confidence": c["confidence"],
            }
            for c in components
        ),
        key=lambda d: d["kcal_sigma"],
        reverse=True,
    )

    return {
        "meal": meal.get("meal", "Snacks"),
        "name": meal.get("name", "Meal"),
        "context": context,
        "components": components,
        "total_kcal": total_kcal,
        "total_grams": total_grams,
        "alcohol_g": total_alcohol,
        "fiber_g": total_fiber,
        **totals,
        "atwater_implied_kcal": implied,
        "atwater_drift": drift,
        "reconciles": reconciles,
        "sigma": sigma,
        "bias": bias,
        "range_low": low,
        "range_high": high,
        "uncertainty_drivers": contributions,
    }


def r5(x):
    """Round to the nearest 5 — signals an estimate rather than false precision."""
    return int(round(x / 5.0) * 5)


def fmt_report(a):
    out = []
    w = 34
    out.append("=" * 68)
    out.append(f"  {a['name']}  —  {a['meal']}")
    out.append("=" * 68)
    out.append("")

    header = f"  {'Component':<{w}}{'g':>6}{'kcal':>7}{'P':>6}{'C':>6}{'F':>6}  conf"
    out.append(header)
    out.append("  " + "-" * (len(header) - 2))
    for c in a["components"]:
        grams = f"{c['grams']:.0f}" if c["grams"] is not None else "-"
        name = c["name"]
        if c["state"]:
            name = f"{name} ({c['state']})"
        if len(name) > w - 1:
            name = name[: w - 2] + "…"
        out.append(
            f"  {name:<{w}}{grams:>6}{c['kcal']:>7.0f}"
            f"{c['protein']:>6.1f}{c['carbs']:>6.1f}{c['fat']:>6.1f}  {c['confidence']}"
        )
    out.append("  " + "-" * (len(header) - 2))
    grams_total = f"{a['total_grams']:.0f}" if a["total_grams"] else "-"
    out.append(
        f"  {'TOTAL':<{w}}{grams_total:>6}{a['total_kcal']:>7.0f}"
        f"{a['protein']:>6.1f}{a['carbs']:>6.1f}{a['fat']:>6.1f}"
    )
    out.append("")

    # Validation
    status = "OK" if a["reconciles"] else "FAILED"
    out.append(
        f"  Atwater check: {status}  "
        f"(macros imply {a['atwater_implied_kcal']:.0f} kcal vs "
        f"{a['total_kcal']:.0f} stated, {a['atwater_drift'] * 100:+.1f}%)"
    )
    if not a["reconciles"]:
        out.append("")
        out.append("  !! Macros and calories do not reconcile. A mass or a density is")
        out.append("     wrong. Fix it before logging — do not report this number.")
        if a["alcohol_g"] == 0 and a["atwater_drift"] < 0:
            out.append("     (Drinks? Alcohol is 7 kcal/g and is not a macro — set")
            out.append("      'alcohol_g' on that component.)")
        if a["fiber_g"] == 0 and a["atwater_drift"] > 0:
            out.append("     (Vegetable-heavy? Fiber sits inside 'carbs' but yields")
            out.append("      ~2 kcal/g, not 4 — set 'fiber_g' to correct for it.)")
    out.append("")

    # Range
    out.append(
        f"  Estimate: {r5(a['total_kcal'])} kcal"
        f"   (range {r5(a['range_low'])}–{r5(a['range_high'])})"
    )
    out.append(
        f"  Context: {a['context']}  |  ±{a['sigma']:.0f} random"
        f"  |  +{a['bias']:.0f} systematic skew"
    )
    drivers = [d for d in a["uncertainty_drivers"] if d["kcal_sigma"] > 1][:3]
    if drivers:
        listed = ", ".join(
            f"{d['name']} (±{d['kcal_sigma']:.0f})" for d in drivers
        )
        out.append(f"  Uncertainty driven by: {listed}")
    out.append("")

    # Lose It! block — suppressed when the macros don't reconcile, so there is
    # nothing paste-ready to copy out of a broken estimate.
    if not a["reconciles"]:
        out.append("  (Lose It! block withheld — fix the reconciliation first.)")
        out.append("")
        return "\n".join(out)

    out.append("-" * 68)
    out.append("  LOSE IT!  —  QUICK ADD")
    out.append("-" * 68)
    out.append(f"  Meal:     {a['meal']}")
    out.append(f"  Name:     {a['name']}")
    out.append(f"  Calories: {r5(a['total_kcal'])}")
    out.append(f"  Protein:  {a['protein']:.0f} g")
    out.append(f"  Carbs:    {a['carbs']:.0f} g")
    out.append(f"  Fat:      {a['fat']:.0f} g")
    out.append("-" * 68)
    out.append("")

    out.append("  Per-component (for logging against database entries):")
    for c in a["components"]:
        grams = f"{c['grams']:.0f} g" if c["grams"] is not None else "-"
        out.append(
            f"    {c['name']} — {grams} — {c['kcal']:.0f} kcal, "
            f"{c['protein']:.0f}P / {c['carbs']:.0f}C / {c['fat']:.0f}F"
        )
    out.append("")
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("meal", help="path to the meal JSON file, or '-' for stdin")
    p.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON instead"
    )
    args = p.parse_args(argv)

    try:
        if args.meal == "-":
            meal = json.load(sys.stdin)
        else:
            with open(args.meal, encoding="utf-8") as fh:
                meal = json.load(fh)
    except FileNotFoundError:
        print(f"error: no such file: {args.meal}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.meal}: {exc}", file=sys.stderr)
        return 2

    try:
        analysis = analyze(meal)
    except MealError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print(fmt_report(analysis))

    # Non-zero exit when the macros don't reconcile, so a caller notices.
    return 0 if analysis["reconciles"] else 1


if __name__ == "__main__":
    sys.exit(main())
