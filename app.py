"""
Flask API for the A/B Test Significance Engine.
"""
import os
from flask import Flask, request, jsonify, send_from_directory

from stats_engine import (
    two_proportion_z_test,
    welch_t_test,
    chi_square_test,
    required_sample_size,
)
from data_loader import get_conversion_summary, get_gamerounds_by_group

app = Flask(__name__)


@app.route("/", methods=["GET"])
def dashboard():
    return send_from_directory(os.path.dirname(__file__), "dashboard.html")


@app.route("/api/test/proportions", methods=["POST"])
def test_proportions():
    body = request.get_json(force=True)
    try:
        result = two_proportion_z_test(
            conversions_a=body["conversions_a"],
            n_a=body["n_a"],
            conversions_b=body["conversions_b"],
            n_b=body["n_b"],
        )
        return jsonify(result)
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/test/means", methods=["POST"])
def test_means():
    body = request.get_json(force=True)
    try:
        result = welch_t_test(body["sample_a"], body["sample_b"])
        return jsonify(result)
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/test/chi-square", methods=["POST"])
def test_chi_square():
    body = request.get_json(force=True)
    try:
        result = chi_square_test(body["observed"])
        return jsonify(result)
    except (KeyError, ValueError, ZeroDivisionError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/test/sample-size", methods=["GET"])
def sample_size():
    try:
        baseline = float(request.args.get("baseline_rate"))
        mde = float(request.args.get("min_detectable_effect"))
        n = required_sample_size(baseline, mde)
        return jsonify({"required_sample_size_per_group": n})
    except (TypeError, ValueError):
        return jsonify({"error": "pass baseline_rate and min_detectable_effect as query params"}), 400


@app.route("/api/cookie-cats/<metric>", methods=["GET"])
def cookie_cats_retention(metric):
    try:
        summary = get_conversion_summary(metric)
        a, b = summary["gate_30"], summary["gate_40"]
        result = two_proportion_z_test(
            conversions_a=a["converted"], n_a=a["n"],
            conversions_b=b["converted"], n_b=b["n"],
        )
        result["group_a"] = "gate_30"
        result["group_b"] = "gate_40"
        result["metric"] = metric
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/cookie-cats/gamerounds", methods=["GET"])
def cookie_cats_gamerounds():
    try:
        a, b = get_gamerounds_by_group()
        result = welch_t_test(a, b)
        result["group_a"] = "gate_30"
        result["group_b"] = "gate_40"
        result["metric"] = "sum_gamerounds"
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
