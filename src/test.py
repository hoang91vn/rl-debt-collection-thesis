from datetime import datetime
from typing import Any, Dict, List
from clients_code import Client
import numpy as np
import pandas as pd
import os
from abt import run
from constants import RUN_DATA_PATH, PLAYGROUND_DIR, CURRENT_DIR

if not os.path.exists(RUN_DATA_PATH):
    os.makedirs(RUN_DATA_PATH)
if __name__ == "__main__":
    generator = np.random.default_rng(42)
    run(
        RUN_DATA_PATH,
        20260501,
        2,
        2,
        generator=generator,
        start_date=20240501,
        overwrite=True,
    )
