"""
Phase 3: Monte Carlo Simulation & Stress Testing

For validated walk-forward variants, performs:
1. Bootstrap Monte Carlo - Resample annual returns for confidence intervals
2. Stress period analysis - Examine behavior during known stress periods
3. Statistical significance testing
4. Risk metrics calculation

Usage:
    cd /Users/t/_repos/extremevalue/research-kit
    uv run python scripts/develop/run_phase3_analysis.py /Users/t/_repos/research
"""

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation."""
    n_simulations: int
    mean_cagr: float
    median_cagr: float
    cagr_5th_percentile: float
    cagr_95th_percentile: float
    prob_positive: float  # Probability of positive return
    prob_beat_spy: float  # Probability of beating 10% annual (rough SPY average)
    worst_case_cagr: float
    best_case_cagr: float


@dataclass
class StressTestResult:
    """Results from stress period analysis."""
    period_name: str
    period_year: int
    return_pct: float
    sharpe: float
    max_drawdown: float
    recovery_assessment: str  # "strong", "moderate", "weak"


@dataclass
class Phase3Result:
    """Complete Phase 3 analysis result."""
    variant_id: str
    timestamp: str

    # Walk-forward summary
    wf_sharpe: float
    wf_consistency: float
    wf_max_drawdown: float
    annual_returns: List[float]

    # Monte Carlo results
    monte_carlo: MonteCarloResult

    # Stress test results
    stress_tests: List[StressTestResult]

    # Overall assessment
    risk_adjusted_score: float  # Combined score
    confidence_level: str  # "high", "medium", "low"
    recommendation: str
    concerns: List[str]

    def to_dict(self) -> Dict:
        return {
            "variant_id": self.variant_id,
            "timestamp": self.timestamp,
            "walk_forward": {
                "sharpe": self.wf_sharpe,
                "consistency": self.wf_consistency,
                "max_drawdown": self.wf_max_drawdown,
                "annual_returns": self.annual_returns,
            },
            "monte_carlo": {
                "n_simulations": self.monte_carlo.n_simulations,
                "mean_cagr": self.monte_carlo.mean_cagr,
                "median_cagr": self.monte_carlo.median_cagr,
                "cagr_5th_percentile": self.monte_carlo.cagr_5th_percentile,
                "cagr_95th_percentile": self.monte_carlo.cagr_95th_percentile,
                "prob_positive": self.monte_carlo.prob_positive,
                "prob_beat_spy": self.monte_carlo.prob_beat_spy,
                "worst_case_cagr": self.monte_carlo.worst_case_cagr,
                "best_case_cagr": self.monte_carlo.best_case_cagr,
            },
            "stress_tests": [
                {
                    "period": st.period_name,
                    "year": st.period_year,
                    "return": st.return_pct,
                    "sharpe": st.sharpe,
                    "max_drawdown": st.max_drawdown,
                    "recovery": st.recovery_assessment,
                }
                for st in self.stress_tests
            ],
            "assessment": {
                "risk_adjusted_score": self.risk_adjusted_score,
                "confidence_level": self.confidence_level,
                "recommendation": self.recommendation,
                "concerns": self.concerns,
            },
        }


def bootstrap_resample(returns: List[float], n_years: int = 10) -> float:
    """
    Bootstrap resample annual returns to simulate multi-year performance.

    Args:
        returns: List of annual returns (as percentages)
        n_years: Number of years to simulate

    Returns:
        Simulated CAGR over n_years
    """
    # Sample with replacement
    sampled = [random.choice(returns) for _ in range(n_years)]

    # Calculate compound return
    compound = 1.0
    for r in sampled:
        compound *= (1 + r / 100)

    # Convert to CAGR
    cagr = (compound ** (1 / n_years) - 1) * 100
    return cagr


def run_monte_carlo(
    annual_returns: List[float],
    n_simulations: int = 10000,
    n_years: int = 10,
) -> MonteCarloResult:
    """
    Run Monte Carlo simulation on annual returns.

    Args:
        annual_returns: List of annual returns from walk-forward (as percentages)
        n_simulations: Number of Monte Carlo simulations
        n_years: Years to project forward

    Returns:
        MonteCarloResult with distribution statistics
    """
    simulated_cagrs = []

    for _ in range(n_simulations):
        cagr = bootstrap_resample(annual_returns, n_years)
        simulated_cagrs.append(cagr)

    # Sort for percentile calculations
    simulated_cagrs.sort()

    # Calculate statistics
    n = len(simulated_cagrs)
    mean_cagr = sum(simulated_cagrs) / n
    median_cagr = simulated_cagrs[n // 2]
    cagr_5th = simulated_cagrs[int(n * 0.05)]
    cagr_95th = simulated_cagrs[int(n * 0.95)]

    prob_positive = sum(1 for c in simulated_cagrs if c > 0) / n
    prob_beat_spy = sum(1 for c in simulated_cagrs if c > 10) / n  # 10% rough SPY average

    return MonteCarloResult(
        n_simulations=n_simulations,
        mean_cagr=round(mean_cagr, 2),
        median_cagr=round(median_cagr, 2),
        cagr_5th_percentile=round(cagr_5th, 2),
        cagr_95th_percentile=round(cagr_95th, 2),
        prob_positive=round(prob_positive, 3),
        prob_beat_spy=round(prob_beat_spy, 3),
        worst_case_cagr=round(min(simulated_cagrs), 2),
        best_case_cagr=round(max(simulated_cagrs), 2),
    )


def analyze_stress_periods(windows: List[Dict]) -> List[StressTestResult]:
    """
    Analyze performance during known stress periods.

    Args:
        windows: List of window results from walk-forward

    Returns:
        List of stress test results
    """
    stress_tests = []

    # Define stress periods based on years
    stress_definitions = {
        2022: ("2022 Bear Market", "bear"),  # Fed rate hikes, inflation
        # 2020 would be COVID crash but our data starts 2021
    }

    for w in windows:
        year = w["test_year"]
        if year in stress_definitions:
            period_name, _ = stress_definitions[year]

            # Assess recovery based on next year's performance
            next_year_return = None
            for w2 in windows:
                if w2["test_year"] == year + 1:
                    next_year_return = w2["total_return"]
                    break

            if next_year_return is not None:
                if next_year_return > 20:
                    recovery = "strong"
                elif next_year_return > 10:
                    recovery = "moderate"
                else:
                    recovery = "weak"
            else:
                recovery = "unknown"

            stress_tests.append(StressTestResult(
                period_name=period_name,
                period_year=year,
                return_pct=w["total_return"],
                sharpe=w["sharpe"],
                max_drawdown=w["max_drawdown"],
                recovery_assessment=recovery,
            ))

    return stress_tests


def calculate_risk_adjusted_score(
    wf_sharpe: float,
    consistency: float,
    max_drawdown: float,
    mc_prob_positive: float,
    mc_cagr_5th: float,
) -> float:
    """
    Calculate a combined risk-adjusted score (0-100).

    Weights:
    - Walk-forward Sharpe: 30%
    - Consistency: 20%
    - Drawdown (inverted): 20%
    - Monte Carlo prob positive: 15%
    - Monte Carlo 5th percentile: 15%
    """
    # Normalize each component to 0-100 scale
    sharpe_score = min(100, max(0, wf_sharpe * 50))  # 2.0 Sharpe = 100
    consistency_score = consistency * 100  # Already 0-1
    drawdown_score = max(0, 100 - max_drawdown * 2)  # 50% DD = 0
    prob_score = mc_prob_positive * 100  # Already 0-1

    # 5th percentile: positive is good, very negative is bad
    pct5_score = min(100, max(0, 50 + mc_cagr_5th))  # -50% = 0, 0% = 50, +50% = 100

    # Weighted combination
    score = (
        sharpe_score * 0.30 +
        consistency_score * 0.20 +
        drawdown_score * 0.20 +
        prob_score * 0.15 +
        pct5_score * 0.15
    )

    return round(score, 1)


def determine_confidence_and_recommendation(
    score: float,
    wf_sharpe: float,
    consistency: float,
    mc_prob_positive: float,
    mc_cagr_5th: float,
    stress_tests: List[StressTestResult],
) -> Tuple[str, str, List[str]]:
    """
    Determine confidence level and recommendation.

    Returns:
        Tuple of (confidence_level, recommendation, concerns)
    """
    concerns = []

    # Check for concerns
    if wf_sharpe < 0.5:
        concerns.append(f"Low walk-forward Sharpe ({wf_sharpe:.2f})")
    if consistency < 0.6:
        concerns.append(f"Low consistency ({consistency*100:.0f}%)")
    if mc_prob_positive < 0.7:
        concerns.append(f"Monte Carlo shows {(1-mc_prob_positive)*100:.0f}% chance of loss")
    if mc_cagr_5th < 0:
        concerns.append(f"5th percentile CAGR is negative ({mc_cagr_5th:.1f}%)")

    # Check stress test performance
    for st in stress_tests:
        if st.return_pct < -25:
            concerns.append(f"Severe loss in {st.period_name} ({st.return_pct:.1f}%)")
        if st.recovery_assessment == "weak":
            concerns.append(f"Weak recovery after {st.period_name}")

    # Determine confidence
    if score >= 70 and len(concerns) == 0:
        confidence = "high"
    elif score >= 50 and len(concerns) <= 2:
        confidence = "medium"
    else:
        confidence = "low"

    # Determine recommendation
    if confidence == "high":
        recommendation = "RECOMMENDED for paper trading"
    elif confidence == "medium":
        if len(concerns) <= 1:
            recommendation = "ACCEPTABLE with monitoring"
        else:
            recommendation = "PROCEED WITH CAUTION"
    else:
        recommendation = "NOT RECOMMENDED without further analysis"

    return confidence, recommendation, concerns


def run_phase3_analysis(
    variant_id: str,
    walk_forward_data: Dict,
) -> Phase3Result:
    """
    Run complete Phase 3 analysis for a single variant.

    Args:
        variant_id: Variant identifier
        walk_forward_data: Walk-forward results dict

    Returns:
        Phase3Result with complete analysis
    """
    # Extract walk-forward metrics
    wf_sharpe = walk_forward_data["aggregate_sharpe"]
    wf_consistency = walk_forward_data["consistency"]
    wf_max_drawdown = walk_forward_data["max_drawdown"]
    windows = walk_forward_data["windows"]

    # Extract annual returns
    annual_returns = [w["total_return"] for w in windows if w["success"]]

    # Run Monte Carlo
    mc_result = run_monte_carlo(annual_returns, n_simulations=10000, n_years=10)

    # Analyze stress periods
    stress_tests = analyze_stress_periods(windows)

    # Calculate risk-adjusted score
    score = calculate_risk_adjusted_score(
        wf_sharpe,
        wf_consistency,
        wf_max_drawdown,
        mc_result.prob_positive,
        mc_result.cagr_5th_percentile,
    )

    # Determine confidence and recommendation
    confidence, recommendation, concerns = determine_confidence_and_recommendation(
        score,
        wf_sharpe,
        wf_consistency,
        mc_result.prob_positive,
        mc_result.cagr_5th_percentile,
        stress_tests,
    )

    return Phase3Result(
        variant_id=variant_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        wf_sharpe=wf_sharpe,
        wf_consistency=wf_consistency,
        wf_max_drawdown=wf_max_drawdown,
        annual_returns=annual_returns,
        monte_carlo=mc_result,
        stress_tests=stress_tests,
        risk_adjusted_score=score,
        confidence_level=confidence,
        recommendation=recommendation,
        concerns=concerns,
    )


def run_phase3_on_validated(workspace_path: Path) -> List[Phase3Result]:
    """
    Run Phase 3 analysis on all validated variants.

    Args:
        workspace_path: Path to research workspace

    Returns:
        List of Phase3Results
    """
    # Load walk-forward results
    wf_path = workspace_path / "validations" / "walk_forward" / "walk_forward_results.json"
    with open(wf_path) as f:
        wf_data = json.load(f)

    print("Phase 3: Monte Carlo & Stress Testing")
    print("=" * 70)
    print(f"Analyzing {wf_data['validated']} validated variants...\n")

    results = []

    for variant_data in wf_data["results"]:
        if variant_data["determination"] != "VALIDATED":
            continue

        variant_id = variant_data["variant_id"]
        print(f"Analyzing {variant_id}...")

        result = run_phase3_analysis(variant_id, variant_data)
        results.append(result)

        # Print summary
        mc = result.monte_carlo
        print(f"  Monte Carlo: Median CAGR {mc.median_cagr:+.1f}% "
              f"(5th: {mc.cagr_5th_percentile:+.1f}%, 95th: {mc.cagr_95th_percentile:+.1f}%)")
        print(f"  Prob Positive: {mc.prob_positive*100:.0f}%, Prob Beat SPY: {mc.prob_beat_spy*100:.0f}%")
        print(f"  Risk Score: {result.risk_adjusted_score:.1f}/100 | {result.confidence_level.upper()}")
        print(f"  --> {result.recommendation}")
        if result.concerns:
            print(f"  Concerns: {', '.join(result.concerns)}")
        print()

    # Save results
    output_path = workspace_path / "validations" / "walk_forward" / "phase3_results.json"
    output_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_analyzed": len(results),
        "results": [r.to_dict() for r in results],
    }
    output_path.write_text(json.dumps(output_data, indent=2))
    print(f"Results saved to: {output_path}")

    # Print final ranking
    print("\n" + "=" * 70)
    print("PHASE 3 RANKING (by Risk-Adjusted Score)")
    print("=" * 70)

    ranked = sorted(results, key=lambda r: r.risk_adjusted_score, reverse=True)
    print(f"{'Rank':<5} {'Variant':<30} {'Score':<8} {'Confidence':<10} {'Recommendation'}")
    print("-" * 90)

    for i, r in enumerate(ranked, 1):
        print(f"{i:<5} {r.variant_id:<30} {r.risk_adjusted_score:<8.1f} {r.confidence_level:<10} {r.recommendation}")

    # Highlight top pick
    top = ranked[0]
    print(f"\n{'='*70}")
    print(f"TOP PICK: {top.variant_id}")
    print(f"{'='*70}")
    print(f"Risk-Adjusted Score: {top.risk_adjusted_score}/100")
    print(f"Walk-Forward Sharpe: {top.wf_sharpe:.2f}")
    print(f"Monte Carlo Median CAGR: {top.monte_carlo.median_cagr:+.1f}%")
    print(f"Monte Carlo 5th Percentile: {top.monte_carlo.cagr_5th_percentile:+.1f}%")
    print(f"Probability of Positive Return: {top.monte_carlo.prob_positive*100:.0f}%")
    print(f"Probability of Beating SPY: {top.monte_carlo.prob_beat_spy*100:.0f}%")
    print(f"Recommendation: {top.recommendation}")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python run_phase3_analysis.py <workspace_path>")
        sys.exit(1)

    workspace_path = Path(sys.argv[1])
    results = run_phase3_on_validated(workspace_path)
