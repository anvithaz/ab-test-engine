# A/B Test Significance Engine

A statistics engine and API for evaluating A/B test results — built from
first principles rather than wrapping `scipy.stats`, so every number is
auditable and explainable.

## Why

"How would you know if an A/B test result is real?" is one of the most
common questions in DA interviews. This project answers it by actually
implementing the math: two-proportion z-tests, Welch's t-test, chi-square
tests of independence, and a minimum-sample-size calculator — validated
against `scipy`/`statsmodels` ground truth (see `validate.py`).

## Structure

- `stats_engine.py` — core statistical tests, implemented from scratch
  (normal CDF via the error function, pooled/unpooled standard errors,
  Welch-Satterthwaite degrees of freedom, Wilson-Hilferty chi-square
  approximation).
- `data_loader.py` — loads the [Cookie Cats A/B test dataset](https://www.kaggle.com/datasets/mursideyarkin/mobile-games-ab-testing-cookie-cats)
  (a real mobile game A/B test on paywall/gate placement) into SQLite and
  runs the group-level aggregation in SQL, not pandas.
- `app.py` — Flask API exposing both generic test endpoints (bring your
  own counts/samples) and endpoints pre-wired to the Cookie Cats dataset.
- `validate.py` — one-off script confirming the engine's output matches
  `scipy`/`statsmodels` on the same inputs.

## Setup

```bash
pip install -r requirements.txt

# Download cookie_cats.csv from Kaggle and place at data/cookie_cats.csv
mkdir -p data
python3 data_loader.py   # builds ab_test.db from the CSV

python3 app.py            # runs on localhost:5001
```

## Endpoints

**Generic — bring your own data:**
- `POST /api/test/proportions` — `{conversions_a, n_a, conversions_b, n_b}`
- `POST /api/test/means` — `{sample_a: [...], sample_b: [...]}`
- `POST /api/test/chi-square` — `{observed: [[...], [...]]}`
- `GET /api/test/sample-size?baseline_rate=0.2&min_detectable_effect=0.02`

**Cookie Cats dataset (once loaded):**
- `GET /api/cookie-cats/retention_1` — day-1 retention, gate_30 vs gate_40
- `GET /api/cookie-cats/retention_7` — day-7 retention
- `GET /api/cookie-cats/gamerounds` — Welch t-test on rounds played

## Example

```bash
curl -X POST localhost:5001/api/test/proportions \
  -H "Content-Type: application/json" \
  -d '{"conversions_a": 200, "n_a": 1000, "conversions_b": 240, "n_b": 1000}'
```

```json
{
  "rate_a": 0.2, "rate_b": 0.24,
  "absolute_lift": 0.04, "relative_lift_pct": 20.0,
  "z_stat": 2.1592, "p_value": 0.030837,
  "significant_at_0.05": true,
  "ci_95_diff": [0.00373, 0.07627]
}
```

## Known limitations (worth knowing, not hiding)

- The t-test and chi-square p-values use normal-distribution approximations
  rather than the exact t/chi-square distributions — accurate for
  reasonably large samples (n > ~30 per group), but will diverge slightly
  from `scipy` on small samples. See `validate.py` for the actual margin.
- No multiple-testing correction (Bonferroni/FDR) if you run several
  metrics against the same test — worth adding if extending this further.
