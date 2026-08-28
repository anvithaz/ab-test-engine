"""
One-off validation script: compares stats_engine.py output against scipy/statsmodels
ground truth. Run once to confirm correctness, not part of the shipped project.
"""
import numpy as np
from scipy import stats as sp_stats
from stats_engine import welch_t_test, chi_square_test, two_proportion_z_test

# --- Welch's t-test ---
np.random.seed(42)
sample_a = np.random.normal(50, 10, 200).tolist()
sample_b = np.random.normal(53, 10, 200).tolist()

mine = welch_t_test(sample_a, sample_b)
t_scipy, p_scipy = sp_stats.ttest_ind(sample_a, sample_b, equal_var=False)
print("Welch t-test")
print("  mine :", mine["t_stat"], mine["p_value"])
print("  scipy:", round(t_scipy, 4), round(p_scipy, 6))
print()

# --- Chi-square ---
observed = [[450, 550], [500, 500]]
mine_chi = chi_square_test(observed)
chi2_scipy, p_chi_scipy, dof, _ = sp_stats.chi2_contingency(observed, correction=False)
print("Chi-square test")
print("  mine :", mine_chi["chi2_stat"], mine_chi["p_value"])
print("  scipy:", round(chi2_scipy, 4), round(p_chi_scipy, 6))
