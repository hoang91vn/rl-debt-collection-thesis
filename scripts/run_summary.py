import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from rl_debt_collection import summary
import pandas as pd

RUN = "runs/thesis_baseline"
SEED = 42
P_POSITIVE = 0.05

def get_action_cost(action):
    return 5

print("computing revenue...", flush=True)
revenue = summary.calculate_revenue(RUN, None, None)
print("computing cost...", flush=True)
cost = summary.calculate_cost(RUN, None, None, get_action_cost)
print(f"seed={SEED} p_positive={P_POSITIVE} revenue={revenue} cost={cost} profit={revenue-cost}", flush=True)

print("reading transactions.csv...", flush=True)
tx = pd.read_csv(f"{RUN}/transactions.csv")
print(f"transactions.csv row count: {len(tx):,}", flush=True)

last = tx.sort_values("period").groupby("aid").last().reset_index()
terminal_wo    = (last["coll_status"] == 8).sum()
total_terminal = len(last)
print(f"terminal aids: {total_terminal:,}", flush=True)
print(f"terminal WRITE_OFF (coll_status==8): {terminal_wo:,}", flush=True)
print(f"default rate: {terminal_wo/total_terminal:.4f} ({terminal_wo/total_terminal*100:.2f}%)", flush=True)
