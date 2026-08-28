# A/B Test Engine — Interview Prep

Work through these without looking at the code first. If you can't answer
one cold, go re-trace that part of `stats_engine.py` before you ship this
on your resume.

---

## 1. "Walk me through what your project does."

30-second version: "I built a statistics engine that implements A/B test
significance testing from scratch instead of calling scipy — two-proportion
z-tests for conversion-rate tests, Welch's t-test for continuous metrics
like revenue-per-user, and chi-square for categorical outcomes. I validated
every implementation against scipy/statsmodels to confirm correctness, then
wrapped it in a Flask API and ran it against a real mobile game A/B test
dataset."

---

## 2. "Why pooled standard error for the z-test but unpooled for the CI?"

- The hypothesis test asks: *assuming there's no real difference (H0: p_a = p_b),
  how surprising is what we observed?* Under H0 there's only one true
  proportion, so you pool both samples to estimate it — `p_pool = (conv_a + conv_b) / (n_a + n_b)`.
- The confidence interval isn't testing a hypothesis — it's describing the
  *actual observed* difference, where p_a and p_b are allowed to differ.
  So you use each group's own variance (unpooled SE) instead.
- One-liner if pressed: "pooled because H0 assumes one true rate, unpooled
  because the CI describes what we actually saw."

## 3. "Why doesn't Welch's t-test assume equal variances?"

- The classic Student's t-test assumes both groups have the same variance —
  fine in a designed experiment, often false in practice (e.g. the variant
  group might have more variable behavior than control).
- Welch's version computes each group's variance separately in the standard
  error (`var_a/n_a + var_b/n_b`), so unequal variances don't bias the result.
- Cost: degrees of freedom become non-integer (Welch-Satterthwaite formula)
  instead of the clean `n_a + n_b - 2`.
- Rule of thumb to state out loud: "when in doubt, use Welch's — it's strictly
  safer than assuming equal variance and rarely costs you power."

## 4. "Your p-values use a normal approximation, not the real t/chi-square
distribution — why, and what does it cost you?"

- Computing the exact t-distribution or chi-square CDF needs the incomplete
  beta/gamma functions, which I didn't want to hand-roll — the normal
  approximation is accurate once n is reasonably large (~30+ per group),
  which covers most real A/B tests.
- Cost: on small samples the tails are wrong — the real t-distribution has
  fatter tails, so my p-values will be *slightly too small* (falsely
  confident) when n is small.
- I quantified this in `validate.py`: on n=200/group it differed from scipy
  at the 5th-6th decimal place — negligible. State the number if asked,
  it shows you actually checked rather than assumed.

## 5. "How would you decide how much traffic/time you need before calling
a test done?"

- This is what `required_sample_size()` answers — you decide your baseline
  rate, the minimum effect size worth caring about (MDE), and your desired
  power (usually 80%) *before* running the test.
- Key point to make: peeking at a test early and stopping as soon as you see
  significance is a classic mistake (p-hacking via optional stopping) —
  sample size should be fixed in advance, not decided by whether the result
  "looks good yet."

## 6. "What's a limitation of your engine you'd fix if you had more time?"

Have a real answer ready, don't say "nothing" — that reads as not having
thought about it. Good options, pick one you actually understand:
- No multiple-testing correction — if you test 5 metrics at once, some will
  hit p<0.05 by chance alone (Bonferroni or Benjamini-Hochberg would fix this).
- No sequential testing support (can't safely check a test mid-flight without
  invalidating the p-value).
- Two-proportion test breaks down at very small counts (<5 per cell) — a
  Fisher's exact test would be more appropriate there.

## 7. "Why is retention a more interesting outcome to test than plain conversion?"

- Conversion is a single binary event; retention (day-1, day-7) captures
  behavior *over time* — a gate could boost short-term conversion while
  hurting long-term engagement, which is exactly the kind of nuance a
  single-metric test would miss. That's why the Cookie Cats dataset having
  both retention_1 and retention_7 makes it a better test bed than a plain
  ad-click dataset.

---

## Quick self-test

Cover the answers above and try to explain #2 and #3 out loud in under
30 seconds each — those two are the ones most likely to get asked first.
