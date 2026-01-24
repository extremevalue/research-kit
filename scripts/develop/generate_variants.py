"""
Variant Generator for Regime Rotation Strategy

Generates all combinations of:
- 3 structures (regime_switch, tactical_rotation, core_satellite)
- 3 aggressiveness levels (conservative, moderate, aggressive)
- 3 leverage levels (1x, 1.5x, 2x)
- Multiple regime signals
- Multiple re-entry signals

Total: 27 base variants × signal combinations
"""

import json
import itertools
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

from jinja2 import Environment, FileSystemLoader


@dataclass
class VariantConfig:
    """Configuration for a single variant."""
    variant_id: str
    name: str

    # Structure
    structure_type: str  # regime_switch, tactical_rotation, core_satellite
    aggressiveness: str  # conservative, moderate, aggressive
    leverage: float

    # Universe
    symbols: List[str]
    leveraged_symbols: Dict[str, str]  # original -> leveraged mapping

    # Regime signal
    regime_signal_type: str
    regime_signal_lookback: int
    regime_signal_threshold: float

    # Re-entry signal
    reentry_signal_type: str
    reentry_signal_lookback: int
    reentry_signal_threshold: float

    # Weights
    risk_on_weights: Dict[str, float]
    risk_off_weights: Dict[str, float]

    # Position sizing
    position_sizing_method: str
    vol_lookback: int = 21

    # Rebalance
    rebalance_frequency: str = "weekly"

    # Flags
    use_mcclellan: bool = False
    use_vix: bool = False


# Base universe
BASE_SYMBOLS = ["SPY", "GLD", "DBMF"]
LEVERAGED_SYMBOLS = {
    "SPY": "UPRO",  # 3x SPY
    "GLD": "UGL",   # 2x Gold
}

# Weight configurations by aggressiveness
WEIGHT_CONFIGS = {
    "conservative": {
        "risk_on": {"SPY": 0.50, "GLD": 0.25, "DBMF": 0.25},
        "risk_off": {"SPY": 0.35, "GLD": 0.35, "DBMF": 0.30},
    },
    "moderate": {
        "risk_on": {"SPY": 0.60, "GLD": 0.20, "DBMF": 0.20},
        "risk_off": {"SPY": 0.25, "GLD": 0.40, "DBMF": 0.35},
    },
    "aggressive": {
        "risk_on": {"SPY": 0.80, "GLD": 0.10, "DBMF": 0.10},
        "risk_off": {"SPY": 0.10, "GLD": 0.50, "DBMF": 0.40},
    },
}

# Regime signals to test
REGIME_SIGNALS = [
    {"type": "sma_200", "lookback": 200, "threshold": 0},
    {"type": "sma_cross", "lookback": 200, "threshold": 0},  # 50/200 cross
    {"type": "momentum_roc", "lookback": 63, "threshold": 0},  # 3-month momentum
    {"type": "vix_threshold", "lookback": 5, "threshold": 25},
    {"type": "mcclellan", "lookback": 1, "threshold": -50},
]

# Re-entry signals to test
REENTRY_SIGNALS = [
    {"type": "rsi_oversold", "lookback": 14, "threshold": 30},
    {"type": "drawdown", "lookback": 50, "threshold": 0.10},  # 10% from high
    {"type": "vix_spike", "lookback": 5, "threshold": 35},
]

# Structure configurations
STRUCTURES = ["regime_switch", "tactical_rotation", "core_satellite"]
AGGRESSIVENESS = ["conservative", "moderate", "aggressive"]
LEVERAGE_LEVELS = [1.0, 1.5, 2.0]
REBALANCE_FREQUENCIES = ["daily", "weekly", "monthly"]


def generate_variant_id(structure: str, aggr: str, leverage: float,
                        regime_sig: str, reentry_sig: str, rebalance: str,
                        position_sizing: str = "fixed") -> str:
    """Generate a unique variant ID."""
    # Map regime signals to unique short codes
    regime_codes = {
        "sma_200": "S200",
        "sma_cross": "SCRS",
        "momentum_roc": "MROC",
        "vix_threshold": "VIXT",
        "mcclellan": "MCCL",
    }
    # Map re-entry signals to unique short codes
    reentry_codes = {
        "rsi_oversold": "RSI",
        "drawdown": "DD",
        "vix_spike": "VSP",
    }
    parts = [
        structure[:3].upper(),
        aggr[:3].upper(),
        f"L{int(leverage*10)}",  # L10, L15, L20
        regime_codes.get(regime_sig, regime_sig[:4].upper()),
        reentry_codes.get(reentry_sig, reentry_sig[:3].upper()),
        rebalance[0].upper(),
        "V" if position_sizing == "volatility_adjusted" else "F",
    ]
    return "_".join(parts)


def generate_variant_name(config: VariantConfig) -> str:
    """Generate human-readable name without special characters."""
    return (f"{config.structure_type.replace('_', ' ').title()} "
            f"{config.aggressiveness} {config.leverage}x "
            f"{config.regime_signal_type}")


def create_variant(
    structure: str,
    aggressiveness: str,
    leverage: float,
    regime_signal: Dict,
    reentry_signal: Dict,
    rebalance: str,
    position_sizing: str = "fixed",
) -> VariantConfig:
    """Create a variant configuration."""

    weights = WEIGHT_CONFIGS[aggressiveness]

    # Determine if we need special data
    use_mcclellan = regime_signal["type"] == "mcclellan"
    use_vix = regime_signal["type"] == "vix_threshold" or reentry_signal["type"] == "vix_spike"

    # Get leveraged symbols if using leverage
    lev_symbols = LEVERAGED_SYMBOLS if leverage > 1.0 else {}

    variant_id = generate_variant_id(
        structure, aggressiveness, leverage,
        regime_signal["type"], reentry_signal["type"], rebalance,
        position_sizing,
    )

    config = VariantConfig(
        variant_id=variant_id,
        name="",  # Will be set below
        structure_type=structure,
        aggressiveness=aggressiveness,
        leverage=leverage,
        symbols=BASE_SYMBOLS,
        leveraged_symbols=lev_symbols,
        regime_signal_type=regime_signal["type"],
        regime_signal_lookback=regime_signal["lookback"],
        regime_signal_threshold=regime_signal["threshold"],
        reentry_signal_type=reentry_signal["type"],
        reentry_signal_lookback=reentry_signal["lookback"],
        reentry_signal_threshold=reentry_signal["threshold"],
        risk_on_weights=weights["risk_on"],
        risk_off_weights=weights["risk_off"],
        position_sizing_method=position_sizing,
        rebalance_frequency=rebalance,
        use_mcclellan=use_mcclellan,
        use_vix=use_vix,
    )
    config.name = generate_variant_name(config)
    return config


def generate_all_variants(
    include_all_signals: bool = False,
    limit_signals: int = 2,
) -> List[VariantConfig]:
    """Generate all variant combinations.

    Args:
        include_all_signals: If True, generate all signal combinations
        limit_signals: If not including all, limit to first N of each signal type
    """
    variants = []

    # Limit signals for Phase 1 screening
    regime_sigs = REGIME_SIGNALS if include_all_signals else REGIME_SIGNALS[:limit_signals]
    reentry_sigs = REENTRY_SIGNALS if include_all_signals else REENTRY_SIGNALS[:limit_signals]
    rebalances = REBALANCE_FREQUENCIES if include_all_signals else ["weekly"]

    for structure in STRUCTURES:
        for aggr in AGGRESSIVENESS:
            for leverage in LEVERAGE_LEVELS:
                for regime_sig in regime_sigs:
                    for reentry_sig in reentry_sigs:
                        for rebalance in rebalances:
                            # Test both fixed and vol-adjusted sizing
                            for sizing in ["fixed", "volatility_adjusted"]:
                                variant = create_variant(
                                    structure=structure,
                                    aggressiveness=aggr,
                                    leverage=leverage,
                                    regime_signal=regime_sig,
                                    reentry_signal=reentry_sig,
                                    rebalance=rebalance,
                                    position_sizing=sizing,
                                )
                                variants.append(variant)

    return variants


def render_variant_code(variant: VariantConfig, template_dir: Path) -> str:
    """Render variant to QuantConnect Python code."""
    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("regime_rotation.py.j2")

    # Build context
    context = {
        "class_name": f"RegimeRotation_{variant.variant_id}",
        "metadata": {
            "id": variant.variant_id,
            "name": variant.name,
            "description": f"Regime rotation: {variant.structure_type}, {variant.aggressiveness}, {variant.leverage}x",
        },
        "strategy_type": "regime_rotation",
        "schema_version": "2.0",
        "universe": {
            "symbols": variant.symbols,
            "leveraged_symbols": variant.leveraged_symbols if variant.leverage > 1.0 else None,
        },
        "signal": {
            "lookback_days": max(variant.regime_signal_lookback, 200),
        },
        "regime_signal": {
            "type": variant.regime_signal_type,
            "lookback": variant.regime_signal_lookback,
            "threshold": variant.regime_signal_threshold,
        },
        "reentry_signal": {
            "type": variant.reentry_signal_type,
            "lookback": variant.reentry_signal_lookback,
            "threshold": variant.reentry_signal_threshold,
        },
        "structure": {
            "type": variant.structure_type,
            "aggressiveness": variant.aggressiveness,
            "risk_on_weights": variant.risk_on_weights,
            "risk_off_weights": variant.risk_off_weights,
            "reentry_boost": 0.10,
            "momentum_lookback": 63,
            "top_n": 2,
            "core_pct": 0.6,
        },
        "position_sizing": {
            "leverage": variant.leverage,
            "method": variant.position_sizing_method,
            "vol_lookback": variant.vol_lookback,
        },
        "rebalance": {
            "frequency": variant.rebalance_frequency,
        },
        "use_mcclellan": variant.use_mcclellan,
        "use_vix": variant.use_vix,
    }

    return template.render(**context)


def generate_phase1_variants(output_dir: Path, workspace_path: Path) -> List[Dict]:
    """Generate Phase 1 screening variants (reduced set).

    Returns list of variant metadata for tracking.
    """
    template_dir = Path(__file__).parent.parent.parent / "research_system" / "codegen" / "templates"

    # Phase 1: Test core combinations (limited signals, weekly rebalance only)
    variants = generate_all_variants(include_all_signals=False, limit_signals=2)

    print(f"Generating {len(variants)} Phase 1 variants...")

    output_dir.mkdir(parents=True, exist_ok=True)
    variant_metadata = []

    for i, variant in enumerate(variants):
        # Create project directory
        project_dir = output_dir / variant.variant_id
        project_dir.mkdir(exist_ok=True)

        # Render code
        code = render_variant_code(variant, template_dir)

        # Write main.py
        (project_dir / "main.py").write_text(code)

        # Write config.json
        config = {
            "algorithm-language": "Python",
            "parameters": {},
            "description": variant.name,
        }
        (project_dir / "config.json").write_text(json.dumps(config, indent=2))

        variant_metadata.append({
            "variant_id": variant.variant_id,
            "name": variant.name,
            "project_dir": str(project_dir),
            "structure": variant.structure_type,
            "aggressiveness": variant.aggressiveness,
            "leverage": variant.leverage,
            "regime_signal": variant.regime_signal_type,
            "reentry_signal": variant.reentry_signal_type,
            "position_sizing": variant.position_sizing_method,
        })

        if (i + 1) % 10 == 0:
            print(f"  Generated {i + 1}/{len(variants)}")

    # Save variant index
    index_path = output_dir / "variant_index.json"
    index_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": 1,
        "total_variants": len(variant_metadata),
        "variants": variant_metadata,
    }, indent=2))

    print(f"Generated {len(variants)} variants to {output_dir}")
    print(f"Variant index: {index_path}")

    return variant_metadata


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_variants.py <workspace_path>")
        sys.exit(1)

    workspace_path = Path(sys.argv[1])
    output_dir = workspace_path / "validations" / "rotation_variants"

    variants = generate_phase1_variants(output_dir, workspace_path)
    print(f"\nReady to run Phase 1 screening on {len(variants)} variants")
