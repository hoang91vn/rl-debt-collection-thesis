import pandas as pd
from typing import Final, Dict, Tuple, List
import os
import pickle
from rl_types import Statistics, StatisticsDict

ROOT_PATH: Final[str] = os.path.dirname(os.path.dirname(__file__))
PYTHON_DIRECTORY_PATH: Final[str] = os.path.join(ROOT_PATH, "python")
VARIABLES_PATH: Final[str] = os.path.join(PYTHON_DIRECTORY_PATH, "variables")

ONLY_STATE: Final[bool] = False

# with open(os.path.join(VARIABLES_PATH, "statistics.pkl"), "rb") as f:
#    STATISTICS: StatisticsDict = pickle.load(f)


STATE_VARIABLES: Final[List[str]] = [
    "act_paid_installments",
    "act_due",
    "act_age",
    "app_income",
    "app_loan_amount",
    "app_n_installments",
    "app_number_of_children",
]

DISCRETE_VARIABLES: Final[Dict[str, List[int]]] = {
    "coll_status": [1, 2, 3, 4, 5, 6, 7],
    "app_nom_gender": [0, 1],
    "app_nom_marital_status": [1, 2, 3, 4],
    "app_nom_branch": [1, 2, 3, 4],
    "app_nom_job_code": [1, 2, 3, 4],
    "app_nom_cars": [1, 2],
    "app_nom_home_status": [1, 2, 3],
    "app_nom_city": [1, 2, 3, 4],
}

EXTRA_VARIABLES: Final[List[str]] = [
    "installment",
]


def get_statistics(data: pd.DataFrame) -> StatisticsDict:
    data = transform_observation_frame(data)
    statistics = calculate_statistics(data)
    return statistics


def calculate_statistics(abt: pd.DataFrame) -> StatisticsDict:
    statistics: StatisticsDict = {}
    for variable, is_discrete in get_all_variables():
        statistics[variable] = {
            "std": abt[variable].std(),
            "mean": abt[variable].mean(),
            "min": abt[variable].min(),
            "max": abt[variable].max(),
            "is_discrete": is_discrete,
        }
    return statistics


# discrete variables already one hot encoded
def get_all_variables() -> List[Tuple[str, bool]]:
    variables: List[Tuple[str, bool]] = []
    for key in STATE_VARIABLES:
        variables.append((key, False))
    for key, values in DISCRETE_VARIABLES.items():
        for value in values:
            variables.append((f"{key}_{value}", True))
    for key in EXTRA_VARIABLES:
        variables.append((key, False))
    return variables


def get_extra_variables(series: pd.Series) -> pd.Series:
    series["installment"] = series["app_loan_amount"] / series["app_n_installments"]
    return series


def get_discrete_variables(series: pd.Series) -> pd.Series:
    new_columns = {}
    for discrete_variable, values in DISCRETE_VARIABLES.items():
        for value in values:
            new_columns[f"{discrete_variable}_{value}"] = 0
        new_columns[f"{discrete_variable}_{int(series[discrete_variable])}"] = 1

    # Concatenate new columns to the observation
    series = pd.concat([series, pd.Series(new_columns)])

    series = series.drop(labels=list(DISCRETE_VARIABLES.keys()), axis=0)

    return series


def get_state_space_size() -> int:
    state_space_size: int = 0
    state_space_size += len(STATE_VARIABLES)
    if ONLY_STATE:
        return state_space_size
    for key, values in DISCRETE_VARIABLES.items():
        state_space_size += len(values)
    state_space_size += len(EXTRA_VARIABLES)
    return state_space_size


MINMAX_MINIMUMS_MAXIMUMS: Final[Dict[str, Tuple[float, float]]] = {
    "app_income": (0, 20000),
    "app_loan_amount": (0, 50000),
    "app_n_installments": (0, 100),
    "app_number_of_children": (0, 10),
    "act_paid_installments": (0, 100),
    "act_due": (0, 100),
    "act_age": (0, 100),
    # "installment": (0, 1000),
}

STD_MEANS_STDS: Final[Dict[str, Tuple[float, float]]] = {
    "app_income": (10000, 5000),
    "app_loan_amount": (25000, 10000),
    "app_n_installments": (50, 20),
    "app_number_of_children": (5, 2),
    "act_paid_installments": (50, 20),
    "act_due": (50, 20),
    "act_age": (50, 20),
}


def normalize_minmax_series(
    min_value: float, max_value: float, series: pd.Series
) -> pd.Series:
    return (series - min_value) / (max_value - min_value)


def normalize_std_series(mean: float, std: float, series: pd.Series) -> pd.Series:
    return (series - mean) / std


def transform_observation(observation: pd.Series) -> pd.Series:
    new_columns = {}
    for discrete_variable, values in DISCRETE_VARIABLES.items():
        for value in values:
            new_columns[f"{discrete_variable}_{value}"] = 0
        new_columns[f"{discrete_variable}_{int(observation[discrete_variable])}"] = 1

    # Concatenate new columns to the observation
    observation = pd.concat([observation, pd.Series(new_columns)])

    observation = observation.drop(labels=list(DISCRETE_VARIABLES.keys()), axis=0)

    return observation


def get_extra_variables_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame["installment"] = frame["app_loan_amount"] / frame["app_n_installments"]
    return frame


def transform_observation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    variables = STATE_VARIABLES + list(DISCRETE_VARIABLES.keys())
    frame = frame[variables]
    frame = get_extra_variables_frame(frame)
    # for key, (min_value, max_value) in MINMAX_MINIMUMS_MAXIMUMS.items():
    #     frame[key] = normalize_minmax_series(min_value, max_value, frame[key])
    # if some key of the series is not in numbers, show a warning
    # for key in STATE_VARIABLES:
    #     if key not in MINMAX_MINIMUMS_MAXIMUMS.keys():
    #         print(f"Warning: {key} is not in numbers")

    # one hot encode DISCRETE_VARIABLES
    for discrete_variable, values in DISCRETE_VARIABLES.items():
        for value in values:
            frame.loc[:, f"{discrete_variable}_{value}"] = frame.loc[
                :, discrete_variable
            ].apply(lambda x: 1 if x == value else 0)
    # drop original columns
    frame = frame.drop(labels=list(DISCRETE_VARIABLES.keys()), axis=1)

    return frame


def normalize_with_minmax(series: pd.Series) -> pd.Series:
    for key, (min_value, max_value) in MINMAX_MINIMUMS_MAXIMUMS.items():
        series[key] = normalize_minmax_series(min_value, max_value, series[key])
    return series


def normalize_with_statistics(
    series: pd.Series, statistics: StatisticsDict, with_discrete: bool, minmax: bool
) -> pd.Series:
    for key, statistic in statistics.items():
        if statistic["is_discrete"] and not with_discrete:
            continue
        if minmax:
            series[key] = normalize_minmax_series(
                statistic["min"], statistic["max"], series[key]
            )
        else:
            series[key] = (series[key] - statistic["mean"]) / statistic["std"]
    return series


def transform(abt_data: pd.Series, statistics: StatisticsDict) -> pd.Series:
    # print(abt_data)
    if not ONLY_STATE:
        variables = STATE_VARIABLES + list(DISCRETE_VARIABLES.keys())
        abt_data = abt_data[variables]
        abt_data = get_extra_variables(abt_data)
        abt_data = get_discrete_variables(abt_data)
    else:
        abt_data = abt_data[STATE_VARIABLES]
    abt_data = normalize_with_statistics(abt_data, statistics, False, False)
    return abt_data
