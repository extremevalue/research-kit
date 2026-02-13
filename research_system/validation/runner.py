"""V4 Runner - Orchestrates the complete validation pipeline.

Pipeline steps:
1. Load V4 strategy YAML
2. Generate QuantConnect Python code (template or LLM)
3. Run backtest via LEAN CLI (local or cloud)
4. Parse results (Sharpe, drawdown, CAGR)
5. Apply validation gates from config
6. Update status (move to validated/invalidated)
7. Save results
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from research_system.codegen.v4_generator import V4CodeGenerator, V4CodeGenResult
from research_system.validation.backtest import (
    BacktestExecutor,
    BacktestResult,
    WalkForwardResult,
)

import logging

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Result of a V4 pipeline run."""

    strategy_id: str
    success: bool
    determination: str = "PENDING"  # VALIDATED, INVALIDATED, BLOCKED, FAILED
    code_gen: V4CodeGenResult | None = None
    backtest: WalkForwardResult | None = None
    gate_results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "strategy_id": self.strategy_id,
            "success": self.success,
            "determination": self.determination,
            "code_gen": self.code_gen.to_dict() if self.code_gen else None,
            "backtest": self.backtest.to_dict() if self.backtest else None,
            "gate_results": self.gate_results,
            "error": self.error,
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
        }


class Runner:
    """Orchestrates the complete V4 validation pipeline.

    The runner handles:
    - Strategy loading from workspace
    - Code generation (template or LLM)
    - Backtest execution (local or cloud)
    - Gate application from V4Config
    - Status updates and file management
    - Result persistence
    """

    def __init__(
        self,
        workspace,
        llm_client=None,
        use_local: bool = False,
        num_windows: int = 1,
    ):
        """Initialize the V4 runner.

        Args:
            workspace: V4Workspace instance
            llm_client: Optional LLM client for code generation
            use_local: Use local Docker instead of QC cloud
            num_windows: Number of walk-forward windows (1, 2, or 5)
        """
        self.workspace = workspace
        self.llm_client = llm_client
        self.use_local = use_local
        self.num_windows = num_windows

        # Initialize code generator
        self.code_generator = V4CodeGenerator(llm_client)

        # Load config for gates
        self._config = workspace.config

        # Initialize backtest executor
        self.backtest_executor = BacktestExecutor(
            workspace_path=workspace.path,
            use_local=use_local,
            cleanup_on_start=not use_local,
            num_windows=num_windows,
            timeout=self._config.backtest.timeout,
        )

    def run(
        self,
        strategy_id: str,
        dry_run: bool = False,
        force_llm: bool = False,
        skip_verify: bool = False,
        force: bool = False,
    ) -> RunResult:
        """Run the full pipeline for a single strategy.

        Args:
            strategy_id: Strategy ID (e.g., "STRAT-001")
            dry_run: If True, show what would happen without executing
            force_llm: Force LLM code generation instead of template
            skip_verify: If True, skip verification check
            force: If True, re-run blocked strategies by moving them back to pending

        Returns:
            RunResult with pipeline outcome
        """
        logger.info(f"Running V4 pipeline for {strategy_id}")

        # Step 1: Load strategy
        strategy = self._load_strategy(strategy_id)
        if strategy is None:
            return RunResult(
                strategy_id=strategy_id,
                success=False,
                determination="FAILED",
                error=f"Strategy not found: {strategy_id}",
            )

        current_status = self._get_strategy_status(strategy_id)
        if current_status == "blocked":
            if force:
                print(f"  --force: Moving {strategy_id} from blocked to pending")
                self._update_status(strategy_id, "pending")
                self._reset_strategy_status(strategy_id)
            else:
                return RunResult(
                    strategy_id=strategy_id,
                    success=False,
                    determination="BLOCKED",
                    error=f"Strategy is blocked (use --force to retry)",
                )

        # Step 1b: Run verification check (unless skipped)
        if not skip_verify and not dry_run:
            from research_system.validation import V4Verifier, VerificationStatus

            print(f"  Checking verification status...")
            verifier = V4Verifier(self.workspace)
            verify_result = verifier.verify(strategy)

            if verify_result.overall_status == VerificationStatus.FAIL:
                print(f"    FAILED - {verify_result.failed} verification failures")
                print(f"    Run 'research v4-verify {strategy_id}' to see details")
                return RunResult(
                    strategy_id=strategy_id,
                    success=False,
                    determination="BLOCKED",
                    error=f"Verification failed: {verify_result.failed} failures",
                )
            elif verify_result.overall_status == VerificationStatus.WARN:
                print(f"    PASSED with {verify_result.warnings} warning(s)")
            else:
                print(f"    PASSED")

        # Dry run: show what would happen
        if dry_run:
            return self._dry_run(strategy_id, strategy)

        # Step 2: Generate code (with retry for extraction failures)
        print(f"  Generating backtest code for {strategy_id}...")
        max_codegen_attempts = 3
        code_result = None
        for codegen_attempt in range(1, max_codegen_attempts + 1):
            code_result = self._generate_code(strategy, force_llm)
            if code_result.success:
                break
            # Only retry if the failure is an extraction issue (LLM ran but output wasn't parseable)
            is_extraction_failure = code_result.error and (
                "did not contain valid Python code" in code_result.error
                or "Could not extract" in code_result.error
            )
            if not is_extraction_failure or codegen_attempt >= max_codegen_attempts:
                break
            print(f"    Code extraction failed (attempt {codegen_attempt}/{max_codegen_attempts}), retrying...")

        if not code_result.success:
            return RunResult(
                strategy_id=strategy_id,
                success=False,
                determination="FAILED",
                code_gen=code_result,
                error=f"Code generation failed: {code_result.error}",
            )

        # Save generated code
        self._save_code(strategy_id, code_result.code)
        print(f"    Method: {code_result.method}")
        if code_result.template_used:
            print(f"    Template: {code_result.template_used}")

        # Step 3: Run walk-forward backtest
        print(f"  Running walk-forward validation...")

        # Use correction loop if LLM is available
        correction_attempts = 1
        if self.llm_client:
            wf_result, correction_attempts = self.backtest_executor.run_walk_forward_with_correction(
                code=code_result.code,
                strategy_id=strategy_id,
                strategy=strategy,
                code_generator=self.code_generator,
            )
            if correction_attempts > 1:
                print(f"    Code corrected after {correction_attempts} attempts")
        else:
            wf_result = self.backtest_executor.run_walk_forward(
                code=code_result.code,
                strategy_id=strategy_id,
            )

        # Check for blocking issues
        if wf_result.determination in ("BLOCKED", "RETRY_LATER"):
            # Only move to blocked folder for permanent issues, not transient ones
            if not wf_result.is_transient:
                self._update_status(strategy_id, "blocked")
                print(f"  Strategy blocked: {wf_result.determination_reason}")
            else:
                # Transient issue - leave in pending for retry
                print(f"  Transient failure (will retry): {wf_result.determination_reason}")

            self._save_result(strategy_id, RunResult(
                strategy_id=strategy_id,
                success=False,
                determination=wf_result.determination,
                code_gen=code_result,
                backtest=wf_result,
                error=wf_result.determination_reason,
            ))
            return RunResult(
                strategy_id=strategy_id,
                success=False,
                determination=wf_result.determination,
                code_gen=code_result,
                backtest=wf_result,
                error=wf_result.determination_reason,
            )

        # Print window results
        for w in wf_result.windows:
            if w.result.success:
                print(f"    Window {w.window_id}: CAGR={w.result.cagr*100:.1f}%, Sharpe={w.result.sharpe:.2f}")
            else:
                print(f"    Window {w.window_id}: FAILED - {w.result.error}")

        # Print aggregates
        if wf_result.aggregate_sharpe is not None:
            cagr_str = f", CAGR={wf_result.aggregate_cagr*100:.1f}%" if wf_result.aggregate_cagr is not None else ""
            print(f"  Aggregate: Sharpe={wf_result.aggregate_sharpe:.2f}, Consistency={wf_result.consistency*100:.0f}%{cagr_str}")
            if wf_result.max_drawdown is not None:
                print(f"             Max DD={wf_result.max_drawdown*100:.1f}%")

        # Step 4: Apply gates
        print(f"  Applying validation gates...")
        gate_results = self._apply_gates(wf_result)
        gates_passed = all(g["passed"] for g in gate_results)

        for gate in gate_results:
            status = "PASS" if gate["passed"] else "FAIL"
            print(f"    {gate['gate']}: {status} (actual={gate['actual']:.2f}, threshold={gate['threshold']:.2f})")

        # Step 5: Determine outcome
        if gates_passed:
            determination = "VALIDATED"
            new_status = "validated"
        else:
            determination = "INVALIDATED"
            new_status = "invalidated"

        # Step 6: Update status
        print(f"  Result: {determination}")
        self._update_status(strategy_id, new_status)

        # Step 7: Save results
        result = RunResult(
            strategy_id=strategy_id,
            success=True,
            determination=determination,
            code_gen=code_result,
            backtest=wf_result,
            gate_results=gate_results,
        )
        self._save_result(strategy_id, result)

        return result

    def run_all(
        self,
        dry_run: bool = False,
        force_llm: bool = False,
        skip_verify: bool = False,
    ) -> list[RunResult]:
        """Run pipeline for all pending strategies.

        Args:
            dry_run: If True, show what would happen without executing
            force_llm: Force LLM code generation
            skip_verify: Skip verification check

        Returns:
            List of RunResult for each strategy
        """
        # Get all pending strategies
        strategies = self.workspace.list_strategies(status="pending")
        if not strategies:
            print("No pending strategies to process.")
            return []

        print(f"Found {len(strategies)} pending strategies")
        results = []

        for i, strat in enumerate(strategies, 1):
            strategy_id = strat["id"]
            print(f"\n[{i}/{len(strategies)}] Processing {strategy_id}: {strat.get('name', 'Unknown')}")

            result = self.run(strategy_id, dry_run=dry_run, force_llm=force_llm, skip_verify=skip_verify)
            results.append(result)

            # Summary for this strategy
            if result.success:
                print(f"  -> {result.determination}")
            else:
                print(f"  -> FAILED: {result.error}")

        # Final summary
        print(f"\n{'='*50}")
        print("Summary:")
        validated = sum(1 for r in results if r.determination == "VALIDATED")
        invalidated = sum(1 for r in results if r.determination == "INVALIDATED")
        blocked = sum(1 for r in results if r.determination == "BLOCKED")
        failed = sum(1 for r in results if r.determination == "FAILED")

        print(f"  Validated:   {validated}")
        print(f"  Invalidated: {invalidated}")
        print(f"  Blocked:     {blocked}")
        print(f"  Failed:      {failed}")

        return results

    def _load_strategy(self, strategy_id: str) -> dict[str, Any] | None:
        """Load strategy from workspace."""
        return self.workspace.get_strategy(strategy_id)

    def _get_strategy_status(self, strategy_id: str) -> str | None:
        """Get current status of a strategy."""
        for status in ["pending", "validated", "invalidated", "blocked"]:
            path = self.workspace.strategies_path / status / f"{strategy_id}.yaml"
            if path.exists():
                return status
        return None

    def _generate_code(
        self,
        strategy: dict[str, Any],
        force_llm: bool = False,
    ) -> V4CodeGenResult:
        """Generate backtest code for strategy."""
        return self.code_generator.generate(strategy, force_llm=force_llm)

    def _save_code(self, strategy_id: str, code: str) -> None:
        """Save generated code to validations directory."""
        val_dir = self.workspace.validations_path / strategy_id
        val_dir.mkdir(parents=True, exist_ok=True)
        code_file = val_dir / "backtest.py"
        code_file.write_text(code)

    def _apply_gates(self, wf_result: WalkForwardResult) -> list[dict[str, Any]]:
        """Apply validation gates from config.

        Returns:
            List of gate results with passed/failed status
        """
        gates = []
        config_gates = self._config.gates

        # Sharpe ratio gate
        if wf_result.aggregate_sharpe is not None:
            gates.append({
                "gate": "min_sharpe",
                "threshold": config_gates.min_sharpe,
                "actual": wf_result.aggregate_sharpe,
                "passed": wf_result.aggregate_sharpe >= config_gates.min_sharpe,
            })

        # Consistency gate
        if wf_result.consistency is not None:
            gates.append({
                "gate": "min_consistency",
                "threshold": config_gates.min_consistency,
                "actual": wf_result.consistency,
                "passed": wf_result.consistency >= config_gates.min_consistency,
            })

        # Max drawdown gate
        if wf_result.max_drawdown is not None:
            gates.append({
                "gate": "max_drawdown",
                "threshold": config_gates.max_drawdown,
                "actual": wf_result.max_drawdown,
                "passed": wf_result.max_drawdown <= config_gates.max_drawdown,
            })

        # CAGR gate
        if wf_result.aggregate_cagr is not None:
            gates.append({
                "gate": "min_cagr",
                "threshold": config_gates.min_cagr,
                "actual": wf_result.aggregate_cagr,
                "passed": wf_result.aggregate_cagr >= config_gates.min_cagr,
            })

        return gates

    def _update_status(self, strategy_id: str, new_status: str) -> None:
        """Move strategy to new status directory."""
        current_status = self._get_strategy_status(strategy_id)
        if current_status and current_status != new_status:
            try:
                self.workspace.move_strategy(strategy_id, current_status, new_status)
                logger.info(f"Moved {strategy_id} from {current_status} to {new_status}")
            except Exception as e:
                logger.error(f"Failed to move strategy: {e}")

    def _reset_strategy_status(self, strategy_id: str) -> None:
        """Reset the status field inside the strategy YAML to 'pending'."""
        path = self.workspace.strategies_path / "pending" / f"{strategy_id}.yaml"
        if path.exists():
            try:
                data = yaml.safe_load(path.read_text())
                if isinstance(data, dict) and data.get("status") != "pending":
                    data["status"] = "pending"
                    path.write_text(yaml.dump(data, default_flow_style=False))
                    logger.info(f"Reset {strategy_id} YAML status to pending")
            except Exception as e:
                logger.error(f"Failed to reset strategy status: {e}")

    def _save_result(self, strategy_id: str, result: RunResult) -> None:
        """Save run result to validations directory."""
        val_dir = self.workspace.validations_path / strategy_id
        val_dir.mkdir(parents=True, exist_ok=True)

        # Save full result as JSON
        result_file = val_dir / "run_result.json"
        result_file.write_text(json.dumps(result.to_dict(), indent=2))

        # Save determination summary
        determination_file = val_dir / "determination.json"
        determination_file.write_text(json.dumps({
            "strategy_id": strategy_id,
            "determination": result.determination,
            "timestamp": result.timestamp,
            "gates_passed": [g["gate"] for g in result.gate_results if g["passed"]],
            "gates_failed": [g["gate"] for g in result.gate_results if not g["passed"]],
        }, indent=2))

        # Save backtest results as YAML for human readability
        if result.backtest:
            backtest_file = val_dir / "backtest_results.yaml"
            yaml_data = {
                "strategy_id": strategy_id,
                "aggregate_sharpe": result.backtest.aggregate_sharpe,
                "aggregate_cagr": result.backtest.aggregate_cagr,
                "consistency": result.backtest.consistency,
                "max_drawdown": result.backtest.max_drawdown,
                "mean_return": result.backtest.mean_return,
                "median_return": result.backtest.median_return,
                "windows": [
                    {
                        "id": w.window_id,
                        "period": f"{w.start_date} to {w.end_date}",
                        "cagr": w.result.cagr,
                        "sharpe": w.result.sharpe,
                        "max_drawdown": w.result.max_drawdown,
                        "success": w.result.success,
                    }
                    for w in result.backtest.windows
                ],
            }
            backtest_file.write_text(yaml.dump(yaml_data, default_flow_style=False))

    def _dry_run(self, strategy_id: str, strategy: dict[str, Any]) -> RunResult:
        """Show what would happen without executing."""
        # V4 schema: tags.hypothesis_type (list), entry.type, hypothesis.summary
        tags = strategy.get("tags", {})
        hypothesis_type_list = tags.get("hypothesis_type", [])
        strategy_type = ", ".join(hypothesis_type_list) if hypothesis_type_list else "unknown"
        signal_type = strategy.get("entry", {}).get("type", "unknown")
        description = strategy.get("hypothesis", {}).get("summary", "No description")

        print(f"\n[DRY RUN] Would process {strategy_id}:")
        print(f"  Name: {strategy.get('name', 'Unknown')}")
        print(f"  Type: {strategy_type}")
        print(f"  Signal: {signal_type}")
        print(f"  Description: {description[:80]}...")

        # Check if template would match
        from research_system.codegen.templates.v4 import get_template_for_v4_strategy
        template = get_template_for_v4_strategy(strategy_type, signal_type)
        print(f"  Code generation: {'Template' if template != 'base.py.j2' else 'LLM'}")
        if template != "base.py.j2":
            print(f"    Template: {template}")

        # Show gates
        config_gates = self._config.gates
        print(f"  Gates to apply:")
        print(f"    min_sharpe: {config_gates.min_sharpe}")
        print(f"    min_consistency: {config_gates.min_consistency}")
        print(f"    max_drawdown: {config_gates.max_drawdown}")
        print(f"    min_cagr: {config_gates.min_cagr}")

        print(f"  Walk-forward windows: {self.num_windows}")
        print(f"  Backtest mode: {'Local Docker' if self.use_local else 'QC Cloud'}")

        return RunResult(
            strategy_id=strategy_id,
            success=True,
            determination="PENDING",
            dry_run=True,
        )


# Backward-compat aliases
V4RunResult = RunResult
V4Runner = Runner
