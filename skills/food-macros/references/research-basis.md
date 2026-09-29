# Research Basis

Why this skill is built the way it is. Every design choice in `SKILL.md` traces to
something here.

---

## 1. The accuracy ceiling, honestly stated

Independent validation of AI food-photo estimation, 2024-2026:

| Measure | Finding |
|---|---|
| Food **identification** accuracy | 68-86% |
| **Portion size** estimation accuracy | as low as 39% — the weak link |
| Typical consumer photo app calorie error | 15-30% mean |
| Best independently validated app (PlateLens) | ~13% MAE vs weighed reference |
| **General-purpose LLMs (ChatGPT, Claude), image only** | **just under 40% mean error** for weight and energy |
| Gemini, image only | 65-70% error |
| Macronutrient error, LLMs, image only | 42-110% |

A 2025 study of standardized food photographs also found models **increasingly
underestimate as portions get larger**, even with plates and cutlery in frame for scale.

**Implication:** naive "here's a photo, how many calories" is a ~40% error tool. That's
not good enough to drive a deficit. Everything in this skill exists to close that gap.

## 2. Mass is the highest-leverage input — this is the core finding

From the "cue ladder" work on multimodal nutrition estimation, where models were given
progressively more context (image only → verified ingredient list → total dish mass →
per-ingredient mass):

> Providing just the total mass reduces calorie prediction error across all models,
> making it **the single most impactful cue**. Calorie prediction errors improved from
> approximately **51% in the image-only setting to as low as 29%** when provided with
> total and per-ingredient mass.

Mass beat knowing the ingredient list. It beat cuisine context. It beat chain-of-thought
prompting, which in at least one study **did not improve accuracy for any nutrient**
when the energy estimate itself remained uncertain.

**Implication — and this is the whole design:** the skill's job is not "reason harder
about calories." It's to convert the photo into *grams*, using physical scale references,
and then treat kcal as arithmetic. Hence `portion-anchors.md`, hence the mandatory scale
reference in Step 2, hence the refusal to report a holistic calorie guess.

It also explains why asking the user one targeted question is worth so much: "is that a
6 oz or a 10 oz portion" converts a `low`-confidence mass into a `high`-confidence one,
which is the most valuable single thing that can happen to the estimate.

## 3. Structured decomposition beats holistic estimation

Agentic self-questioning workflows outperformed fixed prompt sequences by 8+ percentage
points, especially in low-context scenarios. Expert-persona and structured reasoning
prompts cut calorie MAE by up to 50% on small evaluation sets.

**Implication:** Step 1's decomposition into single-density components, and the explicit
"state your reasoning in one clause" requirement in Step 3.

## 4. The systematic underestimation bias is large and one-directional

- Diners underestimate restaurant meals by **20-40%**.
- A BMJ study of ~3,400 diners: adults underestimated by ~175 kcal per meal on average,
  teens by ~260, and roughly **a quarter of everyone was off by 500+**.
- The average tracked day underestimates intake by **400-600 kcal**, with about half
  attributable to condiments, cooking fats and beverages.
- Restaurants use **2-4 tbsp of oil or butter per dish** where a home cook uses one —
  240-480 kcal that is invisible in any photograph.

**Implication:** two separate design choices. First, `hidden-calories.md` and the
mandatory Step 5 checklist. Second, the uncertainty band is **asymmetric** — the skew is
applied only to the high side, because the error distribution genuinely is skewed. A
symmetric ± band would misrepresent the risk.

## 5. Raw vs cooked state is a systematic, avoidable error

USDA defines cooking yield as cooked weight ÷ raw weight. Generic chicken breast yields
~72-73%. Rice roughly triples; pasta roughly doubles-and-a-quarter.

Cooking changes weight, not calories. A photo always shows cooked food. Using a raw
density against a cooked mass — or the reverse — is a 1.4× error on meat and a 2.8×
error on rice.

**Implication:** every row in `nutrient-density.md` is state-labelled, conversion factors
live in `portion-anchors.md` §6, and `SKILL.md` requires the state be stated explicitly.

## 6. Atwater reconciliation as a free correctness gate

Protein 4 kcal/g, carbohydrate 4, fat 9, ethanol 7. Fiber and sugar alcohols are the
main sources of legitimate drift (fiber is counted at 4 in general Atwater but yields
~0-2 in practice), which is why the tolerance is 8% rather than tight.

**Implication:** `macro_calc.py` computes it on every meal, exits non-zero on failure,
and **withholds the paste block** when it fails. Arithmetic slips and misplaced decimal
points are a real failure mode for LLM-generated numbers; this catches them
deterministically rather than hoping they get noticed.

## 7. Hand portions need personal calibration

Standard guides put a palm of protein at 85-110 g and a cupped hand at 40-60 g dry grain.
Those are built for an average adult.

**Implication:** Adam is 6'4". His hand is roughly 25-30% larger by volume than the charts
assume, so the generic figures would systematically underestimate every hand-based
portion. `portion-anchors.md` §2 carries adjusted figures and recommends a one-time
two-point calibration with a kitchen scale, which would replace the adjustment with
measured fact.

---

## Sources

Accuracy and validation:
- [Advancements in Using AI for Dietary Assessment Based on Food Images: Scoping Review](https://www.sciencedirect.com/org/science/article/pii/S143888712400791X)
- [Image-based food monitoring and dietary management: a scoping review of calorie counting applications (Frontiers in Nutrition, 2025)](https://www.frontiersin.org/journals/nutrition/articles/10.3389/fnut.2025.1501946/full)
- [The accuracy of portion size estimation using food images and textual descriptions](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9291996/)
- [Review of the validity and feasibility of image-assisted methods for dietary assessment](https://pmc.ncbi.nlm.nih.gov/articles/PMC7686022/)
- [Can We Use AI To Accurately Track Calories with A Picture? (Biolayne)](https://biolayne.com/reps/issue-44/can-we-use-ai-to-accurately-track-calories-with-a-picture/)

LLM-specific estimation:
- [Evaluating Large Multimodal Models for Nutrition Analysis: A Benchmark Enriched with Contextual Metadata](https://arxiv.org/html/2507.07048v1) — the cue-ladder / mass-is-king finding
- [Prompt Engineering and Model Selection for LLM-Based Nutritional Estimation from Food Images](https://pmc.ncbi.nlm.nih.gov/articles/PMC13306177/)
- [Reasoning-Driven Food Energy Estimation via Multimodal Large Language Models](https://pmc.ncbi.nlm.nih.gov/articles/PMC11990770/)
- [Food Portion Estimation: From Pixels to Calories](https://arxiv.org/pdf/2602.05078)

Portion estimation method:
- [Image-based food portion size estimation using a smartphone without a fiducial marker (Public Health Nutrition)](https://www.cambridge.org/core/journals/public-health-nutrition/article/imagebased-food-portion-size-estimation-using-a-smartphone-without-a-fiducial-marker/47ED461DDE607FE0C7E6D70168E80BFA)
- [Development and evaluation of image-series for portion size estimation in dietary assessment among adults](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8057404/)
- [Precision Nutrition hand-portion guide](https://assets.precisionnutrition.com/2019/09/Hand-portion-guide-FF.pdf)

Underestimation and hidden calories:
- [Why You Underestimate Restaurant Calories by 30%](https://calscanai.com/blog/restaurant-calorie-estimation-error-why-you-underestimate/)
- [The Hidden Calories in Dressings, Sauces, and Oils](https://caleye.fit/blog/hidden-calories-dressings-sauces-oils/)

Nutrient data and conversions:
- [USDA FoodData Central API Guide](https://fdc.nal.usda.gov/api-guide) · [free API key signup](https://fdc.nal.usda.gov/api-key-signup/)
- [USDA Food Intakes Converted to Retail Commodities: methodology and yield factors](https://www.ars.usda.gov/ARSUserFiles/80400530/pdf/ficrcd/FICRCD%20Methodology%20and%20User%20Guide.pdf)
- [Open Food Facts API](https://world.openfoodfacts.org/api/v2) — free, no key, good for barcodes
- [Atwater factors and where 4-4-9 breaks down](https://blog.trustwell.com/calorie-calculation-country)

Lose It! integration:
- [cabird/loseit-mcp](https://github.com/cabird/loseit-mcp) — unofficial, can write
- [the-mace/loseit-mcp-local](https://github.com/the-mace/loseit-mcp-local) — read-only, local scrape
- [Validic: Lose It! API Integration for Developers](https://help.validic.com/space/VCS/2010087433/Lose+It!+API+Integration+for+Developers) — enterprise aggregator, not individually accessible
