import os
import saspy
from saspy import SASsession
import pandas as pd
from special_types import AccountHistory, CidAid
from util import (
    get_account_period_info,
    get_all_cidaids,
    get_previous_period,
    save_histories,
)
from decision import decide_for_all
from typing import Dict, List, TypedDict, cast, Final
import traceback
from environment import get_action_cost

# this name will be used to store the corresponding data for the run
RUN_ID: Final[str] = "default"

# SAS code constants
N_DAY: Final[int] = 1
SEED: Final[int] = 1
S_DATE: Final[str] = "01jan2000"
E_DATE: Final[str] = "28feb2001"

# other constants
ROOT_PATH: Final[str] = os.path.dirname(os.path.dirname(__file__))
SAS_DIRECTORY_PATH: Final[str] = os.path.join(ROOT_PATH, "sas")
PYTHON_DIRECTORY_PATH: Final[str] = os.path.join(ROOT_PATH, "python")
HISTORIES_PATH: Final[str] = os.path.join(PYTHON_DIRECTORY_PATH, "histories")
SAS_CODES_PATH: Final[str] = os.path.join(SAS_DIRECTORY_PATH, "codes")
SAS_DATA_PATH: Final[str] = os.path.join(SAS_DIRECTORY_PATH, "data")
INITIAL_PATH: Final[str] = os.path.join(SAS_CODES_PATH, "initial.sas")
ABT_CODE_PATH: Final[str] = os.path.join(SAS_CODES_PATH, "abt_code.sas")
STATISTICS_PATH: Final[str] = os.path.join(PYTHON_DIRECTORY_PATH, "statistics")

os.makedirs(SAS_DATA_PATH, exist_ok=True)
os.makedirs(HISTORIES_PATH, exist_ok=True)
os.makedirs(STATISTICS_PATH, exist_ok=True)


def get_session() -> saspy.SASsession:
    sas = saspy.SASsession(cfgname="winlocal")
    return sas


def initialize(sas: saspy.SASsession) -> None:
    """
    Sets the needed constants for the SAS code and runs the initial SAS codes (everything before the main movemonth loop).
    """
    log: str = ""
    sas.symput("dir", f"{SAS_DIRECTORY_PATH}\\")
    sas.symput("n_day", N_DAY)
    sas.symput("seed", SEED)
    sas.submit(f"%let s_date='{S_DATE}'d;")
    sas.submit(f"%let e_date='{E_DATE}'d;")
    initial_code = open(INITIAL_PATH).read()
    another_code = open(ABT_CODE_PATH).read()
    log += sas.submit(initial_code)["LOG"]
    log += sas.submit(another_code)["LOG"]
    with open(f"{SAS_DATA_PATH}/sas.log", "w") as f:
        f.write(log)


def run_final(
    sas: saspy.SASsession, included_abt_columns: List[str] | None = None
) -> None:
    """
    The main loop of the program. It runs the movemonth1 and movemonth2 SAS macros for each period and lets set the code for choosing actions between them.
    """
    os.makedirs(SAS_DATA_PATH, exist_ok=True)
    log = sas.submit("""
        proc sql noprint;
        select period into :prod_periods separated by '#'
        from data.Production_stat;
        quit;
        %let n_prod_periods=&sqlobs;
        %put &n_prod_periods***&prod_periods;

        %let fperiod=%scan(&prod_periods,1,#);
        %put &fperiod;
        %allocate(&fperiod);
               """)
    with open(f"{SAS_DATA_PATH}/sas.log", "w") as f:
        f.write(log["LOG"])
    n_prod_periods = sas.symget("n_prod_periods")
    n_prod_periods = cast(int, n_prod_periods)
    print("n_prod_periods:", n_prod_periods)

    accounts_histories: Dict[str, AccountHistory] = {}
    total_cost: float = 0.0

    # the main loop processing from period to period
    for fi in range(2, n_prod_periods + 2):
        is_last_period: bool = fi == n_prod_periods + 1
        print(fi)
        sas.symput("fi", fi)
        log = sas.submit(
            """
                        %let fiperiod=%scan(&prod_periods,&fi,#);
	                    %let fiperiod1=%scan(&prod_periods,%eval(&fi-1),#);
                        %movemonth1(&fiperiod,&fiperiod1);
                      """,
            "TEXT",
        )
        with open(f"{SAS_DATA_PATH}/sas.log", "a") as f:
            f.write(log["LOG"])

        fiperiod = str(sas.symget("fiperiod"))
        fiperiod1 = str(sas.symget("fiperiod1"))

        current_period: str = fiperiod1
        previous_period: str = get_previous_period(current_period)
        next_period: str = fiperiod
        print(f"{current_period} -> {next_period}")

        data_collection_actions: pd.DataFrame = sas.sasdata(
            "collection_actions", "data"
        ).to_df()
        transactions: pd.DataFrame = sas.sasdata("transactions", "data").to_df()
        previous_abt: pd.DataFrame | None = None
        try:
            previous_abt = pd.read_sas(
                f"{SAS_DATA_PATH}\\abt_{previous_period}.sas7bdat",
                format="sas7bdat",
                encoding="utf-8",
            )
        except FileNotFoundError:
            print(f"File abt_{previous_period}.sas7bdat not found")
        abt_score = sas.sasdata("abt_score", "data").to_df()

        # list of all aids for which actions should be selected or which were just terminated
        all_cidaids: List[CidAid] = get_all_cidaids(transactions, current_period)
        aids_to_decide: List[str] = []
        for cidaid in all_cidaids:
            cid = cidaid["cid"]
            aid = cidaid["aid"]

            if aid not in accounts_histories:
                accounts_histories[aid] = {
                    "history": [],
                    "terminated": False,
                }
            if previous_abt is None:
                previous_info = None
            else:
                previous_info = get_account_period_info(
                    previous_abt,
                    transactions,
                    data_collection_actions,
                    cid,
                    aid,
                    previous_period,
                    included_abt_columns=included_abt_columns,
                )
            current_info = get_account_period_info(
                abt_score,
                transactions,
                data_collection_actions,
                cid,
                aid,
                current_period,
                included_abt_columns=included_abt_columns,
            )
            assert current_info is not None
            # exchange the last elemenet of the account history with the updated info
            if len(accounts_histories[aid]["history"]) > 0:
                assert previous_info is not None
                accounts_histories[aid]["history"][-1] = previous_info
            accounts_histories[aid]["history"].append(current_info)
            if current_info["transactions_data"]["status"] != "A":
                accounts_histories[aid]["terminated"] = True
            else:
                aids_to_decide.append(cidaid["aid"])
        if not is_last_period:
            collection_actions_sas = sas.sasdata("collection_actions")
            collection_actions = collection_actions_sas.to_df()
            new_collection_actions_rows = pd.DataFrame(
                columns=collection_actions.columns
            )
            decisions: Dict[str, str] = decide_for_all(
                aids_to_decide, accounts_histories
            )
            period_cost: float = 0.0
            for aid in aids_to_decide:
                try:
                    actions_str = decisions[aid]
                    period_cost += get_action_cost(actions_str)
                except KeyError:
                    print("aid not found in decisions:", aid)
                    raise KeyError
                action_nr: int = 1
                for action in actions_str[::-1]:
                    new_row_values = {
                        "cid": accounts_histories[aid]["history"][-1]["cid"],
                        "aid": aid,
                        "period": current_period,
                        "action_nr": float(action_nr),
                        "action": float(action),
                        "coll_status": accounts_histories[aid]["history"][-1][
                            "transactions_data"
                        ]["coll_status"],
                    }
                    new_row = pd.DataFrame(
                        columns=collection_actions.columns, data=[new_row_values]
                    )
                    new_collection_actions_rows = pd.concat(
                        [new_collection_actions_rows, new_row], axis=0
                    )
                    action_nr += 1
            collection_actions_sas.append(new_collection_actions_rows, True)

            debtor_behavior(sas, abt_score)
            sas.submit("%movemonth2(&fiperiod,&fiperiod1);")

            total_cost += period_cost
            statistics = get_statistics()
            # save statistics to csv file for each period
            with open(f"{STATISTICS_PATH}/{RUN_ID}.csv", "a") as f:
                f.write(
                    f"{timestamp},{next_period},{statistics['total_paid_installments']},{statistics['total_amount']},{total_cost},{statistics['total_amount'] - total_cost}\n"
                )

    print("all histories:", len(accounts_histories))
    terminated_histories: Dict[str, AccountHistory] = {
        k: v for k, v in accounts_histories.items() if v["terminated"]
    }
    print("terminated histories:", len(terminated_histories))
    save_histories(terminated_histories, HISTORIES_PATH, RUN_ID)

    # move from SASDATAPATH TO SASDATAPATH with postfix
    os.rename(
        f"{SAS_DATA_PATH}",
        f"{SAS_DATA_PATH}_{RUN_ID}",
    )


def debtor_behavior(
    sas: saspy.SASsession,
    abt_score: pd.DataFrame,
) -> None:
    """
    Computes the the debtor reactions for each account to the actions in the last period. The results are directly written to the SAS sequences table.
    """
    log = sas.submit(
        """
    proc sort data=collection_actions out=actions;
    by aid action_nr;
    run;
    data sequences;
    retain seg 0;
    set actions;
    by aid;
    if first.aid then seg=0;
    seg=seg+(10**(action_nr-1))*action;
    if last.aid;
    positive_reaction=0;
    keep aid seg positive_reaction;
    run;
    """
    )
    with open(f"{SAS_DATA_PATH}/sas.log", "a") as f:
        f.write(log["LOG"])
    sequences_sas = sas.sasdata("sequences")
    sequences = sequences_sas.to_df()
    for _, row in sequences.iterrows():
        aid: str = row["aid"]
        action: str = str(int(row["seg"]))
        positive_reaction: int = 0
        abt_row: pd.Series = abt_score[abt_score["aid"] == aid].iloc[0]
        coll_status = str(int(float(abt_row["coll_status"])))
        match coll_status:
            case "2":
                if action in [
                    "321",
                    "322",
                    "332",
                    "221",
                    "334",
                    "22",
                    "21",
                    "31",
                    "1",
                    "2",
                ]:
                    positive_reaction = 1
            case "3":
                if action in [
                    "321",
                    "322",
                    "332",
                    "221",
                    "334",
                    "22",
                    "21",
                    "31",
                    "1",
                    "2",
                ]:
                    positive_reaction = 1
            case "4":
                if action in [
                    "321",
                    "322",
                    "332",
                    "221",
                    "334",
                    "22",
                    "21",
                    "31",
                    "1",
                    "2",
                ]:
                    positive_reaction = 1
            case "5":
                if action in [
                    "321",
                    "322",
                    "332",
                    "221",
                    "334",
                    "22",
                    "21",
                    "31",
                    "1",
                    "2",
                ]:
                    positive_reaction = 1
            case "6":
                if action in [
                    "321",
                    "322",
                    "332",
                    "221",
                    "334",
                    "22",
                    "21",
                    "31",
                    "1",
                    "2",
                ]:
                    positive_reaction = 1

        sequences.loc[sequences["aid"] == aid, "positive_reaction"] = positive_reaction
    sas.df2sd(sequences, table="sequences", replace=True)


Statistics = TypedDict(
    "Statistics", {"total_paid_installments": int, "total_amount": float}
)


def get_statistics() -> Statistics:
    """
    Reads the production and transactions data and computes the total paid installments and total amount paid.
    """
    production = pd.read_sas(
        f"{SAS_DATA_PATH}\\production.sas7bdat", format="sas7bdat", encoding="utf-8"
    )
    transactions = pd.read_sas(
        f"{SAS_DATA_PATH}\\transactions.sas7bdat", format="sas7bdat", encoding="utf-8"
    )
    # for every account in production, find the last row of given aid in transactions and then multiply the installment from production by paid_installments in transactions
    # then sum all of the values
    total_paid_installments: int = 0
    total_amount: float = 0.0
    for _, row in production.iterrows():
        aid = row["aid"]
        installment = row["installment"]
        aid_transactions = transactions[transactions["aid"] == aid]
        if aid_transactions.empty:
            continue
        last_transaction = aid_transactions.iloc[-1]
        paid_installments = last_transaction["paid_installments"]
        paid_amount: float = installment * paid_installments
        total_paid_installments += paid_installments
        total_amount += paid_amount
    return {
        "total_paid_installments": total_paid_installments,
        "total_amount": total_amount,
    }


sas: SASsession | None = None
try:
    timestamp: str = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    sas = get_session()

    initialize(sas)
    run_final(sas)

except Exception:
    traceback.print_exc()
finally:
    print("disconnecting")
    if sas is not None:
        sas.disconnect()
