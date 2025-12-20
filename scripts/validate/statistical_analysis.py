"""
Statistical analysis for validation results.

Performs significance testing with proper multiple comparison corrections.
Key features:
- Bonferroni correction for multiple tests
- Effect size calculations
- Confidence intervals
- Sample size validation

Usage:
    from scripts.validate.statistical_analysis import analyze_significance
    result = analyze_significance(test_results, n_comparisons=5)
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import get_logger

logger = get_logger("statistical-analysis")


# Statistical thresholds (from constitution)
BASE_ALPHA = 0.01  # Base significance level
MIN_EFFECT_SIZE = 0.1  # Minimum Sharpe improvement for practical significance
MIN_ALPHA_THRESHOLD = 0.01  # 1% annualized alpha minimum


class SignificanceLevel(Enum):
    """Level of statistical significance."""
    HIGHLY_SIGNIFICANT = "highly_significant"  # p < 0.001
    SIGNIFICANT = "significant"                 # p < bonferroni threshold
    MARGINALLY_SIGNIFICANT = "marginal"         # p < 0.05 but > bonferroni
    NOT_SIGNIFICANT = "not_significant"         # p >= 0.05


@dataclass
class TestResult:
    """Result of a single statistical test."""
    test_name: str
    metric: str
    value: float
    p_value: float
    effect_size: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    sample_size: int = 0
    bonferroni_significant: bool = False
    significance_level: SignificanceLevel = SignificanceLevel.NOT_SIGNIFICANT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "metric": self.metric,
            "value": self.value,
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "confidence_interval": list(self.confidence_interval) if self.confidence_interval else None,
            "sample_size": self.sample_size,
            "bonferroni_significant": self.bonferroni_significant,
            "significance_level": self.significance_level.value
        }


@dataclass
class StatisticalAnalysisResult:
    """Complete statistical analysis result."""
    component_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    n_tests: int = 0
    bonferroni_threshold: float = 0.01
    any_significant: bool = False
    practically_significant: bool = False
    tests: List[TestResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "timestamp": self.timestamp,
            "n_tests": self.n_tests,
            "bonferroni_threshold": self.bonferroni_threshold,
            "any_significant": self.any_significant,
            "practically_significant": self.practically_significant,
            "tests": [t.to_dict() for t in self.tests],
            "summary": self.summary
        }


def calculate_bonferroni_threshold(n_tests: int, base_alpha: float = BASE_ALPHA) -> float:
    """
    Calculate Bonferroni-corrected significance threshold.

    Args:
        n_tests: Number of tests being conducted
        base_alpha: Base significance level (default 0.01)

    Returns:
        Corrected threshold (alpha / n_tests)
    """
    if n_tests <= 0:
        return base_alpha
    return base_alpha / n_tests


def calculate_effect_size_sharpe(
    strategy_sharpe: float,
    baseline_sharpe: float
) -> float:
    """
    Calculate effect size as Sharpe ratio improvement.

    A common practical significance threshold is 0.10 improvement.

    Args:
        strategy_sharpe: Strategy's Sharpe ratio
        baseline_sharpe: Baseline Sharpe ratio

    Returns:
        Sharpe improvement (strategy - baseline)
    """
    return strategy_sharpe - baseline_sharpe


def calculate_effect_size_cohens_d(
    mean1: float,
    mean2: float,
    std1: float,
    std2: float,
    n1: int,
    n2: int
) -> float:
    """
    Calculate Cohen's d effect size for comparing two groups.

    Interpretation:
    - Small: d = 0.2
    - Medium: d = 0.5
    - Large: d = 0.8

    Args:
        mean1, mean2: Group means
        std1, std2: Group standard deviations
        n1, n2: Group sample sizes

    Returns:
        Cohen's d effect size
    """
    # Pooled standard deviation
    pooled_std = math.sqrt(
        ((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2)
    )

    if pooled_std == 0:
        return 0.0

    return (mean1 - mean2) / pooled_std


def approximate_p_value_from_sharpe(
    sharpe_improvement: float,
    n_observations: int,
    baseline_sharpe_std: float = 0.3
) -> float:
    """
    Approximate p-value for Sharpe ratio improvement.

    Uses normal approximation for Sharpe ratio distribution.
    Note: This is a simplified approximation. For production use,
    consider bootstrap methods or more sophisticated approaches.

    Args:
        sharpe_improvement: Improvement in Sharpe ratio
        n_observations: Number of return observations
        baseline_sharpe_std: Estimated std of Sharpe ratio (typically 0.2-0.4)

    Returns:
        Approximate two-tailed p-value
    """
    if n_observations <= 0 or baseline_sharpe_std <= 0:
        return 1.0

    # Standard error of Sharpe ratio
    se = baseline_sharpe_std / math.sqrt(n_observations / 252)  # Annualized

    if se == 0:
        return 1.0

    # Z-score
    z = abs(sharpe_improvement) / se

    # Approximate p-value using normal CDF
    # Using simplified approximation without scipy
    # For z > 3, p < 0.003; for z > 2.5, p < 0.01; for z > 2, p < 0.05
    if z > 4:
        return 0.0001
    elif z > 3.5:
        return 0.0005
    elif z > 3:
        return 0.003
    elif z > 2.5:
        return 0.01
    elif z > 2:
        return 0.05
    elif z > 1.5:
        return 0.13
    elif z > 1:
        return 0.32
    else:
        return 0.5 + (0.5 - z * 0.32)  # Rough linear approximation


def calculate_confidence_interval(
    value: float,
    std_error: float,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate confidence interval.

    Args:
        value: Point estimate
        std_error: Standard error
        confidence: Confidence level (default 0.95)

    Returns:
        Tuple of (lower, upper) bounds
    """
    # Z-score for confidence level (approximate)
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    margin = z * std_error
    return (value - margin, value + margin)


def determine_significance_level(
    p_value: float,
    bonferroni_threshold: float
) -> SignificanceLevel:
    """Determine the level of statistical significance."""
    if p_value < 0.001:
        return SignificanceLevel.HIGHLY_SIGNIFICANT
    elif p_value < bonferroni_threshold:
        return SignificanceLevel.SIGNIFICANT
    elif p_value < 0.05:
        return SignificanceLevel.MARGINALLY_SIGNIFICANT
    else:
        return SignificanceLevel.NOT_SIGNIFICANT


def analyze_single_test(
    test_name: str,
    strategy_results: Dict[str, Any],
    baseline_results: Dict[str, Any],
    bonferroni_threshold: float
) -> TestResult:
    """
    Analyze statistical significance of a single test.

    Args:
        test_name: Name of the test
        strategy_results: Results from strategy backtest
        baseline_results: Results from baseline backtest
        bonferroni_threshold: Corrected significance threshold

    Returns:
        TestResult with significance assessment
    """
    # Extract Sharpe ratios
    strategy_sharpe = strategy_results.get("sharpe_ratio", 0) or strategy_results.get("sharpe", 0)
    baseline_sharpe = baseline_results.get("sharpe_ratio", 0) or baseline_results.get("sharpe", 0)

    # Calculate effect size
    effect_size = calculate_effect_size_sharpe(strategy_sharpe, baseline_sharpe)

    # Estimate sample size (trading days)
    n_observations = strategy_results.get("total_days", 252 * 15)  # Default 15 years

    # Approximate p-value
    p_value = approximate_p_value_from_sharpe(effect_size, n_observations)

    # Determine significance
    significance_level = determine_significance_level(p_value, bonferroni_threshold)
    bonferroni_significant = p_value < bonferroni_threshold

    # Calculate confidence interval for Sharpe improvement
    std_error = 0.3 / math.sqrt(n_observations / 252)
    ci = calculate_confidence_interval(effect_size, std_error)

    return TestResult(
        test_name=test_name,
        metric="sharpe_improvement",
        value=effect_size,
        p_value=p_value,
        effect_size=effect_size,
        confidence_interval=ci,
        sample_size=n_observations,
        bonferroni_significant=bonferroni_significant,
        significance_level=significance_level
    )


def analyze_alpha_significance(
    alpha: float,
    n_observations: int,
    bonferroni_threshold: float
) -> TestResult:
    """
    Analyze if alpha is statistically significant.

    Args:
        alpha: Annualized alpha (as decimal, e.g., 0.02 for 2%)
        n_observations: Number of observations
        bonferroni_threshold: Corrected significance threshold

    Returns:
        TestResult for alpha significance
    """
    # Convert to percentage if needed
    if abs(alpha) > 1:
        alpha = alpha / 100

    # Approximate standard error for alpha (typically 2-4% per year)
    alpha_std = 0.03  # 3% annual std as reasonable estimate
    std_error = alpha_std / math.sqrt(n_observations / 252)

    if std_error == 0:
        p_value = 1.0
    else:
        # One-tailed test (alpha > 0)
        z = alpha / std_error
        if z > 3:
            p_value = 0.001
        elif z > 2.5:
            p_value = 0.006
        elif z > 2:
            p_value = 0.023
        elif z > 1.5:
            p_value = 0.067
        elif z > 1:
            p_value = 0.159
        else:
            p_value = 0.5

    significance_level = determine_significance_level(p_value, bonferroni_threshold)
    ci = calculate_confidence_interval(alpha, std_error)

    return TestResult(
        test_name="alpha_significance",
        metric="alpha",
        value=alpha,
        p_value=p_value,
        effect_size=alpha,
        confidence_interval=ci,
        sample_size=n_observations,
        bonferroni_significant=p_value < bonferroni_threshold,
        significance_level=significance_level
    )


def analyze_significance(
    component_id: str,
    test_results: List[Dict[str, Any]],
    baseline_results: Optional[Dict[str, Any]] = None,
    n_comparisons: Optional[int] = None
) -> StatisticalAnalysisResult:
    """
    Perform complete statistical analysis on validation results.

    Args:
        component_id: Catalog entry ID
        test_results: List of test result dicts (each with strategy results)
        baseline_results: Optional baseline for comparison
        n_comparisons: Number of comparisons for Bonferroni (default: len(test_results))

    Returns:
        StatisticalAnalysisResult with all significance assessments
    """
    logger.info(f"Analyzing statistical significance for {component_id}")

    n_tests = n_comparisons if n_comparisons else len(test_results)
    bonferroni_threshold = calculate_bonferroni_threshold(n_tests)

    logger.info(f"  Bonferroni threshold: {bonferroni_threshold:.6f} (n={n_tests})")

    result = StatisticalAnalysisResult(
        component_id=component_id,
        n_tests=n_tests,
        bonferroni_threshold=bonferroni_threshold
    )

    # Default baseline if not provided
    if baseline_results is None:
        baseline_results = {
            "sharpe_ratio": 0.5,  # Typical buy-and-hold baseline
            "alpha": 0,
            "total_days": 252 * 15
        }

    # Analyze each test
    for i, test_data in enumerate(test_results):
        test_name = test_data.get("name", f"test_{i+1}")
        strategy_results = test_data.get("results", test_data)

        # Sharpe improvement test
        test_result = analyze_single_test(
            test_name,
            strategy_results,
            baseline_results,
            bonferroni_threshold
        )
        result.tests.append(test_result)

        # Alpha significance test
        alpha = strategy_results.get("alpha", 0) or strategy_results.get("annual_alpha", 0)
        if alpha:
            n_obs = strategy_results.get("total_days", 252 * 15)
            alpha_test = analyze_alpha_significance(alpha, n_obs, bonferroni_threshold)
            alpha_test.test_name = f"{test_name}_alpha"
            result.tests.append(alpha_test)

    # Summarize results
    significant_tests = [t for t in result.tests if t.bonferroni_significant]
    result.any_significant = len(significant_tests) > 0

    # Check practical significance (effect size)
    sharpe_tests = [t for t in result.tests if t.metric == "sharpe_improvement"]
    practically_significant = any(
        t.effect_size and t.effect_size >= MIN_EFFECT_SIZE
        for t in sharpe_tests
    )
    result.practically_significant = practically_significant and result.any_significant

    result.summary = {
        "total_tests": len(result.tests),
        "significant_count": len(significant_tests),
        "significant_tests": [t.test_name for t in significant_tests],
        "best_effect_size": max((t.effect_size for t in sharpe_tests if t.effect_size), default=0),
        "lowest_p_value": min((t.p_value for t in result.tests), default=1.0),
        "meets_alpha_threshold": any(
            t.metric == "alpha" and t.value >= MIN_ALPHA_THRESHOLD
            for t in result.tests
        ),
        "passes_bonferroni": result.any_significant,
        "practically_significant": result.practically_significant
    }

    # Log summary
    logger.info(f"  Significant tests: {len(significant_tests)}/{len(result.tests)}")
    logger.info(f"  Best effect size: {result.summary['best_effect_size']:.3f}")
    logger.info(f"  Lowest p-value: {result.summary['lowest_p_value']:.6f}")
    logger.info(f"  Practically significant: {result.practically_significant}")

    return result


def validate_sample_size(
    n_observations: int,
    min_years: int = 15,
    trading_days_per_year: int = 252
) -> Tuple[bool, str]:
    """
    Validate if sample size is sufficient for reliable inference.

    Args:
        n_observations: Number of observations
        min_years: Minimum required years
        trading_days_per_year: Trading days per year

    Returns:
        Tuple of (is_valid, message)
    """
    min_observations = min_years * trading_days_per_year

    if n_observations < min_observations:
        years_available = n_observations / trading_days_per_year
        return False, f"Insufficient sample: {years_available:.1f} years < {min_years} minimum"

    return True, f"Sample size OK: {n_observations / trading_days_per_year:.1f} years"


def save_statistical_result(result: StatisticalAnalysisResult, output_dir: Path) -> Path:
    """Save statistical analysis result to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "statistical_analysis.json"

    with open(output_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)

    logger.info(f"Saved statistical analysis to {output_file}")
    return output_file


if __name__ == "__main__":
    # Example usage
    test_results = [
        {
            "name": "mcclellan_filter",
            "results": {
                "sharpe_ratio": 0.85,
                "alpha": 0.025,
                "total_days": 252 * 15
            }
        },
        {
            "name": "breadth_filter",
            "results": {
                "sharpe_ratio": 0.72,
                "alpha": 0.018,
                "total_days": 252 * 15
            }
        }
    ]

    baseline = {
        "sharpe_ratio": 0.55,
        "alpha": 0,
        "total_days": 252 * 15
    }

    result = analyze_significance("IND-002", test_results, baseline)

    print(f"\nStatistical Analysis Result")
    print(f"=" * 50)
    print(f"Component: {result.component_id}")
    print(f"Bonferroni threshold: {result.bonferroni_threshold:.6f}")
    print(f"Any significant: {result.any_significant}")
    print(f"Practically significant: {result.practically_significant}")

    print(f"\nTest Results:")
    for test in result.tests:
        sig = "***" if test.bonferroni_significant else ""
        print(f"  {test.test_name}: p={test.p_value:.4f} effect={test.effect_size:.3f} {sig}")

    print(f"\nSummary:")
    for key, value in result.summary.items():
        print(f"  {key}: {value}")
