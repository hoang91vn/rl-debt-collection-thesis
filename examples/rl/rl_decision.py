import copy
import os
import random
from typing import Dict, Final, List, Literal, Tuple, TypedDict

import pandas as pd
from rl_debt_collection.special_types import (
    AccountHistory,
    AccountPeriodInfo,
)
from rl_types import Statistics, StatisticsDict
import numpy as np
from environment import ACTIONS, get_available_actions, get_action_cost
from transformation import (
    DISCRETE_VARIABLES,
    transform,
    transform_observation,
    get_state_space_size,
    get_statistics,
)
from models import DebtModel, load_or_create_model
from torch.utils.tensorboard.writer import SummaryWriter
import torch

DEVICE: Final[str | None] = None
ROOT_PATH: Final[str] = os.path.dirname(os.path.dirname(__file__))
SAS_DIRECTORY_PATH: Final[str] = os.path.join(ROOT_PATH, "sas")
PYTHON_DIRECTORY_PATH: Final[str] = os.path.join(ROOT_PATH, "python")
MODEL_PATH: Final[str] = f"{PYTHON_DIRECTORY_PATH}\\models\\model.pt"
STATE_SPACE_SIZE: Final[int] = get_state_space_size()

# RUN CONSTANTS
EPSILON: Final[float] = 0.0
GAMMA: Final[float] = 0.9
N_STEPS: Final[int] = 5
LEARNING_RATE: Final[float] = 0.01
ONLY_DECISION: Final[bool] = True
BATCH_SIZE: Final[int] = 32
ITERATIONS: Final[int] = 1000
REWARD_SCHEME: Final[Literal["0", "1"]] = "0"
ONLY_ZEROS: Final[bool] = False

Transition = tuple[pd.Series, str, float, pd.Series | None]


def rl_decide_for_all(
    aids_to_decide: List[str],
    accounts_histories: Dict[str, AccountHistory],
) -> Dict[str, str]:
    generator = np.random.default_rng()
    decisions: Dict[str, str] = {}

    model: DebtModel = load_or_create_model(
        MODEL_PATH, STATE_SPACE_SIZE, len(ACTIONS), DEVICE
    )
    statistics = get_statistics(
        pd.read_sas(
            "C:\\Projects\\rl-debt-collection\\sas\\data_base\\abt_200302.sas7bdat",
            format="sas7bdat",
            encoding="utf-8",
        )
    )
    transformed_accounts_histories = transform_histories(accounts_histories, statistics)

    if not ONLY_DECISION:
        terminated_histories: Dict[str, AccountHistory] = {
            k: v for k, v in transformed_accounts_histories.items() if v["terminated"]
        }
        model_on_history(
            terminated_histories,
            model,
            STATE_SPACE_SIZE,
            len(ACTIONS),
            GAMMA,
            N_STEPS,
            iterations=ITERATIONS,
            batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            whole_buffer=False,
            reward_scheme=REWARD_SCHEME,
            target_network_interval=1,
        )
        torch.save(model.state_dict(), MODEL_PATH)

    for aid in aids_to_decide:
        coll_status = accounts_histories[aid]["history"][-1]["transactions_data"][
            "coll_status"
        ]
        if ONLY_ZEROS:
            action = "0"
        elif coll_status == 1 or coll_status == 7:
            action = "0"
        elif np.random.rand() < EPSILON:
            action = generator.choice(get_available_actions(int(coll_status)))
        else:
            last_info = transformed_accounts_histories[aid]["history"][-1]
            assert last_info["abt_data"] is not None
            last_state = last_info["abt_data"]
            best_action = get_best_action(last_state, model, int(coll_status))
            action = best_action
        decisions[aid] = action
    return decisions


def transform_histories(
    accounts_histories: Dict[str, AccountHistory], statistics: StatisticsDict
) -> Dict[str, AccountHistory]:
    transformed_accounts_histories = copy.deepcopy(accounts_histories)
    for aid, account_history in transformed_accounts_histories.items():
        for i in range(len(account_history["history"])):
            state_data = account_history["history"][i]["abt_data"]
            if state_data is not None:
                account_history["history"][i]["abt_data"] = transform(
                    state_data, statistics=statistics
                )
    return transformed_accounts_histories


def model_on_history(
    accounts_histories: Dict[str, AccountHistory],
    model: DebtModel | None,
    input_size: int,
    output_size: int,
    discount_factor: float,
    n_step: int,
    iterations: int,
    batch_size: int,
    learning_rate: float,
    whole_buffer: bool,
    reward_scheme: Literal["0", "1", "2"],
    target_network_interval: int,
    statistics: StatisticsDict,
) -> DebtModel:
    writer = SummaryWriter()
    print("accounts_histories: ", len(accounts_histories))
    if model is None:
        model = DebtModel(input_size, output_size, DEVICE)
    nonzero_transitions, zero_transitions = get_n_step_transitions_from_raw_episodes(
        accounts_histories,
        n_step,
        discount_factor,
        reward_scheme=reward_scheme,
        statistics=statistics,
    )
    print("nonzero_transitions: ", len(nonzero_transitions))
    print("zero_transitions: ", len(zero_transitions))
    # add 1000 zero_transitions to the replay buffer
    random.shuffle(zero_transitions)

    n_step_buffer: List[Transition] = nonzero_transitions + zero_transitions[:1000]
    print("n_step_buffer: ", len(n_step_buffer))
    # get 80% of n_step_buffer to be used as training buffer
    random.shuffle(n_step_buffer)
    training_buffer = n_step_buffer[: int(0.8 * len(n_step_buffer))]
    validation_buffer = n_step_buffer[int(0.8 * len(n_step_buffer)) :]

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    objective = torch.nn.MSELoss()
    last_validation_loss = float("inf")

    training_values: torch.Tensor | None = None
    training_targets: torch.Tensor | None = None
    validation_values: torch.Tensor | None = None
    validation_targets: torch.Tensor | None = None
    target_model = DebtModel(input_size, output_size, DEVICE)
    for i in range(iterations):
        # update target_model every target_network_interval iterations
        if i % target_network_interval == 0:
            target_model.load_state_dict(model.state_dict())
            target_model = model

        validation_values, validation_targets = get_values_and_targets_from_transitions(
            validation_buffer, discount_factor**n_step, model, model
        )

        # random batch size from training values and targets
        if not whole_buffer:
            batch_indices = np.random.randint(0, len(training_buffer), batch_size)
            batch_transitions = [training_buffer[i] for i in batch_indices]
        else:
            batch_transitions = training_buffer

        training_values, training_targets = get_values_and_targets_from_transitions(
            batch_transitions,
            discount_factor**n_step,
            model,
            target_model,
        )
        loss = update_batch(training_values, training_targets, optimizer, objective)
        validation_loss = objective(validation_values, validation_targets)

        if loss is not None and validation_loss is not None:
            # writer.add_scalars(
            #     "Losses",
            #     {"Training Loss": loss, "Validation Loss": validation_loss},
            #     i,
            # )
            pass
        if i % 10 == 0:
            print(f"iteration: {i}, loss: {loss}, validation loss: {validation_loss}")
            if validation_loss < last_validation_loss:
                torch.save(model.state_dict(), MODEL_PATH)
    writer.close()
    return model


def get_values_and_targets_from_transitions(
    transitions: List[Transition],
    discount_factor: float,
    module: DebtModel,
    target_module: DebtModel,
) -> tuple[torch.Tensor, torch.Tensor]:
    values: torch.Tensor = torch.tensor([], dtype=torch.float32, device=DEVICE)
    targets: torch.Tensor = torch.tensor([], dtype=torch.float32, device=DEVICE)
    for last_state, last_action, reward, current_state in transitions:
        value, target = get_value_and_target(
            last_state,
            last_action,
            reward,
            current_state,
            discount_factor,
            module,
            target_module,
        )
        values = torch.cat([values, value.unsqueeze(0)], 0)
        targets = torch.cat([targets, target.unsqueeze(0)], 0)
    return values, targets


def get_value_and_target(
    state: pd.Series,
    action: str,
    reward: float,
    new_state: pd.Series | None,
    discount_factor: float,
    module: DebtModel,
    targetModule: DebtModel,
    next_value: float | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    if next_value is not None:
        target_value = torch.tensor(
            reward + discount_factor * next_value, dtype=torch.float32, device=DEVICE
        )
    else:
        target_value = get_target_value(
            reward, new_state, discount_factor, targetModule
        )
    current_state_action_value: torch.Tensor = get_state_action_value(
        state, action, module
    )
    return current_state_action_value, target_value


def get_target_value(
    reward: float,
    new_state: pd.Series | None,
    discount_factor: float,
    target_module: DebtModel,
) -> torch.Tensor:
    with torch.no_grad():
        if new_state is None:
            return torch.tensor(reward, dtype=torch.float32, device=DEVICE)
        coll_status = get_coll_status_from_discrete_columns(new_state)
        next_best_action = get_best_action(new_state, target_module, coll_status)
        # new_state_action_values: torch.Tensor = target_module(
        #     torch.tensor(new_state, dtype=torch.float32, device=DEVICE)
        # )
        # max_action_value = new_state_action_values.max(0)[0]
        max_action_value = get_state_action_value(
            new_state, next_best_action, target_module
        )
        target_value: torch.Tensor = reward + discount_factor * max_action_value
    return target_value


def get_best_action(state: pd.Series, module: DebtModel, coll_status: int) -> str:
    best_action = None
    action_values: torch.Tensor = module(torch.tensor(state, dtype=torch.float32))
    # print(action_values)
    # indexes only among the available actions
    available_actions = get_available_actions(coll_status)
    best_action_index = -1
    best_action_value = float("-inf")
    # print("coll_stasus: ", coll_status)
    for available_action in available_actions:
        action_index = ACTIONS.index(available_action)
        action_value = action_values[action_index]
        # print(f"action: {available_action}, value: {action_value}")
        if action_value > best_action_value:
            best_action_value = action_value
            best_action_index = action_index
    best_action = ACTIONS[int(best_action_index)]
    # print("best action: ", best_action)
    return best_action


def get_state_action_value(
    state: pd.Series,
    action: str,
    module: DebtModel,
) -> torch.Tensor:
    current_state_action_values: torch.Tensor = module(
        torch.tensor(state, dtype=torch.float32, requires_grad=True, device=DEVICE)
    )
    # print("INDEX: ", ACTIONS.index(action))
    return current_state_action_values[ACTIONS.index(action)]


def get_coll_status_from_discrete_columns(
    state: pd.Series,
) -> int:
    coll_status = 0
    for key, values in DISCRETE_VARIABLES.items():
        if key == "coll_status":
            for value in values:
                if state[f"{key}_{value}"] == 1:
                    coll_status = value
                    break
    return coll_status


def update_batch(
    values: torch.Tensor,
    targets: torch.Tensor,
    optimizer: torch.optim.Optimizer,
    objective,
) -> torch.Tensor:
    assert values.shape == targets.shape, "Values and targets must have the same shape"
    # print("target: ", targets)
    # print("values: ", values)
    loss = objective(values, targets)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    # print("batch updated")
    return loss


RawEpisode = TypedDict(
    "RawEpisode",
    {
        "transitions": List[Transition],
        "terminated": bool,
    },
)


def get_raw_episodes_from_history(
    accounts_histories: Dict[str, AccountHistory],
    reward_scheme: Literal["0", "1", "2"],
    statistics: StatisticsDict,
) -> List[RawEpisode]:
    raw_episodes: List[RawEpisode] = []
    for aid, account_history in accounts_histories.items():
        transitions: List[Transition] = []
        for i in range(1, len(account_history["history"])):
            previous_info = account_history["history"][i - 1]
            current_info = account_history["history"][i]
            previous_action = previous_info["action"]
            if previous_info["abt_data"] is None or previous_action is None:
                continue
            # print(f"aid: {aid}")
            # print(f"previous: {previous_info['period']}")
            # print(f"current: {current_info['period']}")
            # print(f"sars: {get_sars(previous_info, current_info)}")
            transitions.append(
                get_sars(previous_info, current_info, reward_scheme, statistics)
            )
        raw_episodes.append(
            {
                "transitions": transitions,
                "terminated": account_history["terminated"],
            }
        )
    return raw_episodes


def get_sars(
    previous_info: AccountPeriodInfo,
    current_info: AccountPeriodInfo,
    reward_scheme: Literal["0", "1", "2"],
    statistics: StatisticsDict,
) -> Transition:
    last_state = previous_info["abt_data"]
    last_action = previous_info["action"]
    assert last_state is not None and last_action is not None
    current_state = current_info["abt_data"]
    status = current_info["transactions_data"]["status"]
    terminated: bool = status != "A"
    if terminated:
        current_state = None
    reward: float = calculate_reward(
        previous_info, current_info, reward_scheme, statistics
    )
    return last_state, "".join(last_action), reward, current_state


def calculate_reward(
    previous_info: AccountPeriodInfo,
    current_info: AccountPeriodInfo,
    scheme: Literal["0", "1", "2"],
    statistics: StatisticsDict,
) -> float:
    assert previous_info["abt_data"] is not None
    assert (
        previous_info["abt_data"]["installment"] is not None
        and previous_info["action"] is not None
    )
    installment: float = previous_info["abt_data"]["installment"]
    action_cost: float = get_action_cost(previous_info["action"])
    previous_paid_installments = previous_info["transactions_data"]["paid_installments"]
    current_paid_installments = current_info["transactions_data"]["paid_installments"]
    new_paid_installments = current_paid_installments - previous_paid_installments

    match scheme:
        case "0":
            reward: float = new_paid_installments - 0.75
        case "1":
            reward: float = new_paid_installments * installment - action_cost
        case "2":
            reward: float = new_paid_installments * installment - action_cost
            mean_installment = statistics["installment"]["mean"]
            std_installment = statistics["installment"]["std"]
            std_reward = std_installment
            reward = (reward - mean_installment) / std_reward
    return reward


def get_n_step_transitions_from_raw_episodes(
    accounts_histories: Dict[str, AccountHistory],
    n_step: int,
    gamma: float,
    reward_scheme: Literal["0", "1", "2"],
    statistics: StatisticsDict,
) -> Tuple[List[Transition], List[Transition]]:
    transitions: List[Transition] = []
    zero_transitions: List[Transition] = []
    raw_episodes = get_raw_episodes_from_history(
        accounts_histories, reward_scheme, statistics
    )
    for raw_episode in raw_episodes:
        for i in range(len(raw_episode["transitions"]) - 1, -1, -1):
            last_state, last_action, reward, current_state = raw_episode["transitions"][
                i
            ]
            is_from_1_or_7: bool = last_state["coll_status_1"] in [1] or last_state[
                "coll_status_7"
            ] in [1]
            new_state_index: int = i + n_step
            if new_state_index >= len(raw_episode["transitions"]):
                new_state = None
            else:
                new_state = raw_episode["transitions"][new_state_index][0]
            cumulated_discounted_reward: float = reward
            for j in range(1, n_step):
                if i + j >= len(raw_episode["transitions"]):
                    break
                step_reward = raw_episode["transitions"][i + j][2]
                cumulated_discounted_reward += step_reward * (gamma**j)
            if is_from_1_or_7:
                zero_transitions.append(
                    (last_state, last_action, cumulated_discounted_reward, new_state)
                )
            else:
                transitions.append(
                    (last_state, last_action, cumulated_discounted_reward, new_state)
                )
    return transitions, zero_transitions
