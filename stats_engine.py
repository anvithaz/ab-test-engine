"""
A/B Test Statistical Significance Engine
Implements significance testing from first principles (no scipy.stats shortcuts
for the core math) so the logic is fully auditable and explainable.
"""

import math


# ---------------------------------------------------------------------------
# Core distributions (small self-contained implementations)
# ---------------------------------------------------------------------------

def _erf(x: float) -> float:
    """Abramowitz-Stegun approximation of the error function."""
    sign = 1 if x >= 0 else -1
    x = abs(x)
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
    return sign * y


def normal_cdf(z: float) -> float:
    """Standard normal CDF via the error function."""
    return 0.5 * (1.0 + _erf(z / math.sqrt(2)))


def two_sided_p_from_z(z: float) -> float:
    return 2 * (1 - normal_cdf(abs(z)))


# ---------------------------------------------------------------------------
# Two-proportion z-test (conversion-rate style A/B tests)
# ---------------------------------------------------------------------------

def two_proportion_z_test(conversions_a: int, n_a: int, conversions_b: int, n_b: int,
                           alpha: float = 0.05):
    """
    Compares two conversion rates (e.g. control vs variant).
    Returns rates, absolute/relative lift, z-stat, p-value, and a 95% CI on the difference.
    """
    if n_a == 0 or n_b == 0:
        raise ValueError("Sample sizes must be non-zero")

    p_a = conversions_a / n_a
    p_b = conversions_b / n_b

    # pooled proportion under H0: p_a == p_b
    p_pool = (conversions_a + conversions_b) / (n_a + n_b)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))

    z = 0.0 if se_pool == 0 else (p_b - p_a) / se_pool
    p_value = two_sided_p_from_z(z)

    # unpooled SE for the confidence interval on the difference (standard practice)
    se_diff = math.sqrt((p_a * (1 - p_a)) / n_a + (p_b * (1 - p_b)) / n_b)
    z_crit = 1.959963985  # z for 95% two-sided
    diff = p_b - p_a
    ci_low = diff - z_crit * se_diff
    ci_high = diff + z_crit * se_diff

    relative_lift = (diff / p_a) if p_a > 0 else float("inf")

    return {
        "test": "two_proportion_z_test",
        "rate_a": round(p_a, 5),
        "rate_b": round(p_b, 5),
        "absolute_lift": round(diff, 5),
        "relative_lift_pct": round(relative_lift * 100, 3) if math.isfinite(relative_lift) else None,
        "z_stat": round(z, 4),
        "p_value": round(p_value, 6),
        "significant_at_0.05": p_value < alpha,
        "ci_95_diff": [round(ci_low, 5), round(ci_high, 5)],
        "n_a": n_a,
        "n_b": n_b,
    }


# ---------------------------------------------------------------------------
# Welch's t-test (for continuous metrics, e.g. avg session length, revenue/user)
# ---------------------------------------------------------------------------

def _mean(xs):
    return sum(xs) / len(xs)


def _variance(xs, mean_):
    return sum((x - mean_) ** 2 for x in xs) / (len(xs) - 1)


def welch_t_test(sample_a, sample_b, alpha: float = 0.05):
    """
    Welch's t-test — does not assume equal variances between groups.
    Uses a normal approximation for the p-value (valid for n > ~30 per group;
    for small samples a proper t-distribution CDF would be needed instead).
    """
    n_a, n_b = len(sample_a), len(sample_b)
    if n_a < 2 or n_b < 2:
        raise ValueError("Each sample needs at least 2 observations")

    mean_a, mean_b = _mean(sample_a), _mean(sample_b)
    var_a, var_b = _variance(sample_a, mean_a), _variance(sample_b, mean_b)

    se = math.sqrt(var_a / n_a + var_b / n_b)
    t_stat = 0.0 if se == 0 else (mean_b - mean_a) / se

    # Welch-Satterthwaite degrees of freedom (reported for completeness/interview talking point)
    df_num = (var_a / n_a + var_b / n_b) ** 2
    df_den = ((var_a / n_a) ** 2) / (n_a - 1) + ((var_b / n_b) ** 2) / (n_b - 1)
    df = df_num / df_den if df_den != 0 else float("nan")

    p_value = two_sided_p_from_z(t_stat)  # normal approximation

    z_crit = 1.959963985
    diff = mean_b - mean_a
    ci_low = diff - z_crit * se
    ci_high = diff + z_crit * se

    return {
        "test": "welch_t_test",
        "mean_a": round(mean_a, 5),
        "mean_b": round(mean_b, 5),
        "diff": round(diff, 5),
        "t_stat": round(t_stat, 4),
        "approx_df": round(df, 2),
        "p_value": round(p_value, 6),
        "significant_at_0.05": p_value < alpha,
        "ci_95_diff": [round(ci_low, 5), round(ci_high, 5)],
        "n_a": n_a,
        "n_b": n_b,
    }


# ---------------------------------------------------------------------------
# Chi-square test of independence (for multi-category outcomes, e.g. gate_30 vs gate_40)
# ---------------------------------------------------------------------------

def chi_square_test(observed: list, alpha: float = 0.05):
    """
    observed: 2x2 (or RxC) contingency table, e.g.
        [[retained_a, churned_a],
         [retained_b, churned_b]]
    Uses Wilson-Hilferty approximation to map chi-square stat -> p-value.
    """
    rows = len(observed)
    cols = len(observed[0])
    row_totals = [sum(r) for r in observed]
    col_totals = [sum(observed[r][c] for r in range(rows)) for c in range(cols)]
    grand_total = sum(row_totals)

    chi2 = 0.0
    for r in range(rows):
        for c in range(cols):
            expected = row_totals[r] * col_totals[c] / grand_total
            if expected > 0:
                chi2 += (observed[r][c] - expected) ** 2 / expected

    df = (rows - 1) * (cols - 1)
    p_value = _chi2_sf(chi2, df)

    return {
        "test": "chi_square_test",
        "chi2_stat": round(chi2, 4),
        "degrees_of_freedom": df,
        "p_value": round(p_value, 6),
        "significant_at_0.05": p_value < alpha,
    }


def _chi2_sf(chi2: float, df: int) -> float:
    """Wilson-Hilferty approximation: chi-square survival function via normal approx."""
    if df == 0:
        return 1.0
    z = (((chi2 / df) ** (1 / 3)) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    return 1 - normal_cdf(z)


# ---------------------------------------------------------------------------
# Sample size / power calculator — useful before running a test
# ---------------------------------------------------------------------------

def required_sample_size(baseline_rate: float, min_detectable_effect: float,
                          alpha: float = 0.05, power: float = 0.8) -> int:
    """
    Minimum sample size per group to detect min_detectable_effect (absolute)
    on top of baseline_rate, at given alpha/power. Standard two-proportion formula.
    """
    z_alpha = 1.959963985  # two-sided, alpha=0.05
    z_power = 0.8416212336  # power=0.8

    p1 = baseline_rate
    p2 = baseline_rate + min_detectable_effect
    p_bar = (p1 + p2) / 2

    numerator = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) +
                 z_power * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2

    return math.ceil(numerator / denominator)


if __name__ == "__main__":
    # quick sanity check against a known textbook-style example
    result = two_proportion_z_test(conversions_a=200, n_a=1000, conversions_b=240, n_b=1000)
    print(result)
