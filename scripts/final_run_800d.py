"""
Final production run: 800 clients/day, 60 periods, p_positive=0.00.

Output: artifacts/final_data_800d_60m_p00/
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, Final, List

import numpy as np
import pandas as pd

import rl_debt_collection
from rl_debt_collection import summary

REPO_ROOT = Path(__file__).resolve().parent.parent

CONFIG = {
    "run_label": "final_data_800d_60m_p00",
    "new_clients_count": 800,
    "start_date": 20240501,
    "end_date": 20290501,
    "n_periods": 60,
    "p_positive": 0.00,
    "take_up": 1.0,
    "seed": 42,
    "matrix_tuning": False,
    "simulator_core_modified": False,
    "take_up_implemented": False,
}

RUN_DATA_PATH = REPO_ROOT / "artifacts" / CONFIG["run_label"]
SEED: Final[int] = CONFIG["seed"]
P_POSITIVE: Final[float] = CONFIG["p_positive"]

_reaction_rng: Final[np.random.Generator] = np.random.default_rng(SEED + 1)


def choose_actions(data_path: str, aids: List[str]) -> Dict[str, str]:
    return {aid: "1" for aid in aids}


def simulate_reactions(
    data_path: str, actions: Dict[str, str], period: int
) -> Dict[str, bool]:
    return {aid: bool(_reaction_rng.random() < P_POSITIVE) for aid, _ in actions.items()}


def get_action_cost(action: str) -> int:
    return 5


def save_config(run_dir: Path, wall_sec: float | None = None) -> Path:
    cfg = dict(CONFIG)
    cfg["output_directory"] = str(run_dir)
    cfg["reaction_rng_seed"] = SEED + 1
    if wall_sec is not None:
        cfg["wall_time_seconds"] = round(wall_sec, 1)
        cfg["wall_time_hours"] = round(wall_sec / 3600, 2)
    out = run_dir / "data_generation_config_used.yaml"
    lines = []
    for k, v in cfg.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, float):
            lines.append(f"{k}: {v}")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {v}")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    return out


def pre_launch_summary():
    print("=" * 70)
    print("FINAL PRODUCTION RUN — PRE-LAUNCH SUMMARY")
    print("=" * 70)
    print(f"  Output directory : {RUN_DATA_PATH}")
    print(f"  new_clients_count: {CONFIG['new_clients_count']}/day")
    print(f"  start_date       : {CONFIG['start_date']}")
    print(f"  end_date         : {CONFIG['end_date']}")
    print(f"  n_periods        : {CONFIG['n_periods']}")
    print(f"  p_positive       : {CONFIG['p_positive']}")
    print(f"  seed             : {CONFIG['seed']}")
    print(f"  reaction_rng_seed: {SEED + 1}")
    print(f"  matrix_tuning    : {CONFIG['matrix_tuning']}")
    print(f"  simulator_modified: {CONFIG['simulator_core_modified']}")
    print()
    print("  Expected metrics:")
    print(f"    originations     : ~1,461,600")
    print(f"    post-filter rows : ~535,000")
    print(f"    wall time        : ~14-16 hours")
    print(f"    disk usage       : ~28-32 GB")
    print(f"    peak RAM         : ~12-13 GB")
    print("=" * 70)


def post_run_validation(run_dir: Path, wall_sec: float) -> dict:
    print(f"\n{'=' * 70}")
    print("POST-RUN VALIDATION")
    print(f"{'=' * 70}")

    accounts = pd.read_csv(run_dir / "accounts.csv")
    n_originations = len(accounts)
    print(f"  originations: {n_originations:,}")

    tx = pd.read_csv(run_dir / "transactions.csv")
    print(f"  tx rows: {len(tx):,}")

    last_tx = tx.sort_values(["aid", "period"]).groupby("aid", as_index=False).tail(1)
    n_writeoff = int((last_tx["coll_status"] == 8).sum())
    n_active = int((last_tx["status"] == 1).sum())
    n_closed = int((last_tx["status"] == 3).sum())
    n_default_status = int((last_tx["status"] == 2).sum())
    overall_dr = n_writeoff / max(n_originations, 1)

    first_tx = tx.sort_values(["aid", "period"]).groupby("aid", as_index=False).head(1)
    last_status_per_aid = last_tx.set_index("aid")["coll_status"]
    first_tx["last_coll_status"] = first_tx["aid"].map(last_status_per_aid)
    first_tx["is_writeoff"] = (first_tx["last_coll_status"] == 8).astype(int)

    orig_by_period = first_tx.groupby("fin_period").size()
    wo_by_period = first_tx.groupby("fin_period")["is_writeoff"].sum()
    periods_sorted = sorted(orig_by_period.index)

    burn_in_periods = periods_sorted[:4]
    post_burn_periods = periods_sorted[4:]
    pb_orig = int(orig_by_period.loc[post_burn_periods].sum())
    pb_wo = int(wo_by_period.loc[post_burn_periods].sum())
    pb_dr = pb_wo / max(pb_orig, 1)

    print(f"  overall DR       : {overall_dr * 100:.4f}%")
    print(f"  post-burn-in DR  : {pb_dr * 100:.4f}%")
    print(f"  status A (active): {n_active:,}")
    print(f"  status B (default): {n_default_status:,}")
    print(f"  status C (closed): {n_closed:,}")

    # Phase 2 filter simulation
    MIN_FIN_PERIOD = 202509
    TRAIN_FIN_PERIOD_MAX = 202612
    OOT_FIN_PERIOD_MAX = 202706
    TARGET_MONTHS = 12

    last_sim_period = int(periods_sorted[-1])
    maturity_cutoff = _add_period(last_sim_period, -TARGET_MONTHS)

    eligible = first_tx[
        (first_tx["fin_period"] >= MIN_FIN_PERIOD)
        & (first_tx["fin_period"] <= OOT_FIN_PERIOD_MAX)
        & (first_tx["fin_period"] <= maturity_cutoff)
    ].copy()

    train = eligible[eligible["fin_period"] <= TRAIN_FIN_PERIOD_MAX]
    oot = eligible[
        (eligible["fin_period"] > TRAIN_FIN_PERIOD_MAX)
        & (eligible["fin_period"] <= OOT_FIN_PERIOD_MAX)
    ]

    n_post_filter = len(eligible)
    n_train = len(train)
    n_oot = len(oot)
    train_dr = train["is_writeoff"].mean() if len(train) > 0 else 0
    oot_dr = oot["is_writeoff"].mean() if len(oot) > 0 else 0
    oot_events = int(oot["is_writeoff"].sum())

    print(f"\n  PHASE 2 FILTER SIMULATION:")
    print(f"    MIN_FIN_PERIOD       : {MIN_FIN_PERIOD}")
    print(f"    TRAIN_FIN_PERIOD_MAX : {TRAIN_FIN_PERIOD_MAX}")
    print(f"    OOT_FIN_PERIOD_MAX   : {OOT_FIN_PERIOD_MAX}")
    print(f"    maturity_cutoff      : {maturity_cutoff}")
    print(f"    post-filter rows     : {n_post_filter:,}")
    print(f"    train rows           : {n_train:,}")
    print(f"    OOT rows             : {n_oot:,}")
    print(f"    train DR             : {train_dr * 100:.4f}%")
    print(f"    OOT DR               : {oot_dr * 100:.4f}%")
    print(f"    OOT default count    : {oot_events:,}")

    # Cohort DR table
    print(f"\n  COHORT DEFAULT-RATE TABLE (Phase 2 window):")
    print(f"    {'cohort':>8}  {'orig':>7}  {'wo':>5}  {'DR%':>7}  {'split':>6}")
    for p in sorted(eligible["fin_period"].unique()):
        c = eligible[eligible["fin_period"] == p]
        o = len(c)
        w = int(c["is_writeoff"].sum())
        dr = w / max(o, 1) * 100
        split = "train" if p <= TRAIN_FIN_PERIOD_MAX else "oot"
        print(f"    {int(p):>8}  {o:>7,}  {w:>5}  {dr:>7.3f}  {split:>6}")

    # Acceptance gate
    print(f"\n  ACCEPTANCE GATE:")
    gate_pass = n_post_filter >= 500_000
    print(f"    post-filter rows >= 500,000 ? "
          f"{'PASS' if gate_pass else 'FAIL'} ({n_post_filter:,})")

    result = dict(
        wall_sec=round(wall_sec, 1),
        wall_hr=round(wall_sec / 3600, 2),
        n_originations=n_originations,
        n_tx_rows=len(tx),
        overall_dr_pct=round(overall_dr * 100, 4),
        post_burnin_dr_pct=round(pb_dr * 100, 4),
        n_active=n_active,
        n_default=n_default_status,
        n_closed=n_closed,
        n_post_filter=n_post_filter,
        n_train=n_train,
        n_oot=n_oot,
        train_dr_pct=round(train_dr * 100, 4),
        oot_dr_pct=round(oot_dr * 100, 4),
        oot_events=oot_events,
        gate_pass=gate_pass,
    )

    with open(run_dir / "validation_results.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def _add_period(period: int, months: int) -> int:
    y, m = divmod(period, 100)
    total = y * 12 + (m - 1) + months
    return (total // 12) * 100 + (total % 12) + 1


def main():
    pre_launch_summary()

    RUN_DATA_PATH.mkdir(parents=True, exist_ok=True)
    save_config(RUN_DATA_PATH)
    print(f"\n  Config saved: {RUN_DATA_PATH / 'data_generation_config_used.yaml'}")
    print(f"  Starting simulation at {pd.Timestamp.now().isoformat(timespec='seconds')}")
    print()

    t0 = time.time()
    try:
        rl_debt_collection.run(
            data_path=str(RUN_DATA_PATH),
            end_date=CONFIG["end_date"],
            new_clients_count=CONFIG["new_clients_count"],
            choose_actions_func=choose_actions,
            simulate_reactions_func=simulate_reactions,
            start_date=CONFIG["start_date"],
            overwrite=True,
            generator=np.random.default_rng(SEED),
        )
    except Exception as e:
        wall = time.time() - t0
        print(f"\nSIMULATOR EXCEPTION after {wall / 3600:.2f}h: {type(e).__name__}: {e}")
        save_config(RUN_DATA_PATH, wall)
        sys.exit(1)

    wall = time.time() - t0
    print(f"\n  Simulation complete: {wall / 3600:.2f}h ({wall:.0f}s)")

    save_config(RUN_DATA_PATH, wall)

    print("\n  Running post-simulation validation...")
    result = post_run_validation(RUN_DATA_PATH, wall)

    if result["gate_pass"]:
        print("\n  >>> GATE PASSED. Ready for Phase 1.5 Feature Factory. <<<")
    else:
        print(f"\n  >>> GATE FAILED. Post-filter rows: {result['n_post_filter']:,} < 500,000 <<<")
        print("  >>> Recommend rerun at 900/day or 1000/day. <<<")

    print(f"\n  Results saved: {RUN_DATA_PATH / 'validation_results.json'}")
    print(f"  Config saved:  {RUN_DATA_PATH / 'data_generation_config_used.yaml'}")


if __name__ == "__main__":
    main()
