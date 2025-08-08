from transformation import get_statistics
from rl_debt_collection.util import load_histories, save_histories
from models import DebtModel, load_or_create_model
import os
from typing import Final
from .rl_decision import (
    model_on_history,
    transform_histories,
    get_state_space_size,
)
from environment import ACTIONS
import torch
import pandas as pd

ROOT_PATH: Final[str] = os.path.dirname(os.path.dirname(__file__))
SAS_DIRECTORY_PATH: Final[str] = os.path.join(ROOT_PATH, "sas")
PYTHON_DIRECTORY_PATH: Final[str] = os.path.join(ROOT_PATH, "python")
HISTORIES_PATH: Final[str] = os.path.join(PYTHON_DIRECTORY_PATH, "histories")
SAS_CODES_PATH: Final[str] = os.path.join(SAS_DIRECTORY_PATH, "codes")
SAS_DATA_PATH: Final[str] = os.path.join(SAS_DIRECTORY_PATH, "data")
INITIAL_PATH: Final[str] = os.path.join(SAS_CODES_PATH, "initial.sas")
ABT_CODE_PATH: Final[str] = os.path.join(SAS_CODES_PATH, "abt_code.sas")
MODEL_PATH: Final[str] = f"{PYTHON_DIRECTORY_PATH}\\models\\model.pt"

STATE_SPACE_SIZE: Final[int] = get_state_space_size()
GAMMA: Final[float] = 0.8

statistics = get_statistics(
    pd.read_sas(
        "C:\\Projects\\rl-debt-collection\\sas\\data_base\\abt_200302.sas7bdat",
        format="sas7bdat",
        encoding="utf-8",
    )
)

# Load the histories
histories = load_histories(HISTORIES_PATH, "base")

histories = transform_histories(histories, statistics)

model = model_on_history(
    accounts_histories=histories,
    model=None,
    input_size=STATE_SPACE_SIZE,
    output_size=len(ACTIONS),
    discount_factor=GAMMA,
    n_step=2,
    iterations=100000,
    batch_size=1000,
    learning_rate=0.01,
    whole_buffer=False,
    reward_scheme="1",
    target_network_interval=1,
    statistics=statistics,
)
torch.save(model.state_dict(), MODEL_PATH)
