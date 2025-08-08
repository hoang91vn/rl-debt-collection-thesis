from typing import Dict, TypedDict


Statistics = TypedDict(
    "Statistics",
    {
        "std": float,
        "mean": float,
        "min": float,
        "max": float,
        "is_discrete": bool,
    },
)

StatisticsDict = Dict[str, Statistics]
