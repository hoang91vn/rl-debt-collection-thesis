from datetime import datetime
from typing import Any, Dict, List
from clients_code import Client
import numpy as np
import pandas as pd

if __name__ == "__main__":
    n = 1000000
    generator: np.random.Generator = np.random.default_rng(42)
    current_date: datetime = datetime.now()
    data_frame: pd.DataFrame = pd.DataFrame(
        columns=[
            "cid",
            "date_of_birth",
            "gender",
            "marital_status",
            "job_code",
            "home",
            "city",
            "cars",
            "number_of_children",
            "income",
            "spendings",
            "year",
        ]
    )
    clients: List[Dict[str, Any]] = []
    for i in range(10000):
        # cid is the string of lenght 10, it should be padded from the left with zeros to len 10
        cid: str = str(i).zfill(10)
        client = Client.get_starter(cid, generator, 2, current_date=current_date)
        clients.append(client.to_dict())
    data_frame = pd.DataFrame(clients, columns=data_frame.columns)
    print(data_frame.describe())
    data_frame.to_csv("test.csv", index=False)
