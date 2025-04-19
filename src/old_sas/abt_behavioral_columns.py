import os
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from old_sas.dictionaries import Status, CollStat
from old_sas.constants import RUN_DATA_PATH, CURRENT_DIR, PLAYGROUND_DIR
from other.util import get_relative_period


def make_production_df(
    clients_df: pd.DataFrame, accounts_df: pd.DataFrame
) -> pd.DataFrame:
    # production_df is clients_df and accounts_df joined on cid
    production_df = pd.merge(
        clients_df,
        accounts_df,
        on="cid",
        how="inner",
    )
    return production_df


def make_abt_base(
    production_df: pd.DataFrame, transactions_df: pd.DataFrame, period: int
) -> pd.DataFrame:
    # Filter transactions for active accounts in the given period and earlier
    filtered_transactions = transactions_df[
        (
            transactions_df["aid"].isin(
                transactions_df.loc[
                    (transactions_df["status"] == Status.A)
                    & (transactions_df["period"] == period),
                    "aid",
                ]
            )
        )
        & (transactions_df["period"] <= period)
    ]
    print(filtered_transactions.shape)

    # Merge filtered transactions with production data on 'aid'
    abt_base_tmp = pd.merge(
        filtered_transactions,
        production_df.drop(columns=["cid", "app_date", "period"]),
        on="aid",
        how="left",
    )

    # Fill missing values for unmatched rows
    abt_base_tmp.fillna({"_iorc_": 0}, inplace=True)

    # Create additional characteristics
    abt_base_tmp["act_days"] = abt_base_tmp["pay_days"] + 15
    abt_base_tmp["act_paid_installments"] = abt_base_tmp["paid_installments"]
    abt_base_tmp["act_utl"] = (
        abt_base_tmp["paid_installments"] / abt_base_tmp["n_installments"]
    )
    abt_base_tmp["act_dueutl"] = (
        abt_base_tmp["due_installments"] / abt_base_tmp["n_installments"]
    )
    abt_base_tmp["act_due"] = abt_base_tmp["due_installments"]
    abt_base_tmp["act_age"] = abt_base_tmp["date_of_birth"].apply(
        lambda row: int(
            (
                datetime.strptime(str(period), "%Y%m")
                - datetime.strptime(row, "%Y-%m-%d")
            ).days
            / 365.25
        )
    )
    abt_base_tmp["act_cc"] = (
        abt_base_tmp["installment"] + abt_base_tmp["spendings"]
    ) / abt_base_tmp["income"]
    abt_base_tmp["act_dueinc"] = (
        abt_base_tmp["due_installments"]
        * abt_base_tmp["installment"]
        / abt_base_tmp["income"]
    )
    abt_base_tmp["act_loaninc"] = abt_base_tmp["loan_amount"] / abt_base_tmp["income"]
    abt_base_tmp["app_income"] = abt_base_tmp["income"]
    abt_base_tmp["app_loan_amount"] = abt_base_tmp["loan_amount"]
    abt_base_tmp["app_n_installments"] = abt_base_tmp["n_installments"]
    abt_base_tmp["act_seniority"] = abt_base_tmp["fin_period"].apply(
        lambda row: (
            datetime.strptime(str(row), "%Y%m") - datetime.strptime(str(period), "%Y%m")
        ).days
        // 30
        + 1,
    )

    abt_base_tmp["act_cus_n_loans_hist"] = abt_base_tmp.groupby(["cid"])[
        "aid"
    ].transform("count")
    abt_base_tmp["act_cus_n_statC"] = abt_base_tmp.groupby(["cid"])["status"].transform(
        lambda x: (x == Status.C).sum()
    )
    abt_base_tmp["act_cus_n_statB"] = abt_base_tmp.groupby(["cid"])["status"].transform(
        lambda x: (x == Status.B).sum()
    )
    abt_base_tmp["act_cus_n_loans_act"] = abt_base_tmp.groupby(["cid"])[
        "aid"
    ].transform("count")
    abt_base_tmp["act_cus_sum_installment"] = abt_base_tmp.groupby(["cid"])[
        "installment"
    ].transform("sum")
    abt_base_tmp["act_cus_dum_due"] = abt_base_tmp.groupby(["cid"])[
        "due_installments"
    ].transform(lambda x: (x > 0).sum())
    abt_base_tmp["act_cus_sum_n_installments"] = abt_base_tmp.groupby(["cid"])[
        "n_installments"
    ].transform("sum")
    abt_base_tmp["act_cus_utl"] = (
        abt_base_tmp["act_cus_sum_installment"]
        / abt_base_tmp["act_cus_sum_n_installments"]
    )
    abt_base_tmp["act_cus_dueutl"] = (
        abt_base_tmp["act_cus_dum_due"] / abt_base_tmp["act_cus_sum_n_installments"]
    )
    abt_base_tmp["act_cus_cc"] = (
        abt_base_tmp["act_cus_sum_installment"] + abt_base_tmp["spendings"]
    ) / abt_base_tmp["income"]
    abt_base_tmp["act_cus_seniority"] = abt_base_tmp.groupby(["cid"])[
        "act_seniority"
    ].transform("max")

    # Add nominal and other characteristics
    abt_base_tmp["app_nom_branch"] = abt_base_tmp["branch"]
    abt_base_tmp["app_nom_gender"] = abt_base_tmp["gender"]
    abt_base_tmp["app_nom_job_code"] = abt_base_tmp["job_code"]
    abt_base_tmp["app_number_of_children"] = abt_base_tmp["number_of_children"]
    abt_base_tmp["app_nom_marital_status"] = abt_base_tmp["marital_status"]
    abt_base_tmp["app_nom_city"] = abt_base_tmp["city"]
    abt_base_tmp["app_nom_home_status"] = abt_base_tmp["home_status"]
    abt_base_tmp["app_nom_cars"] = abt_base_tmp["cars"]
    abt_base_tmp["app_spendings"] = abt_base_tmp["spendings"]

    # Filter for the given period and select relevant columns
    abt_base = abt_base_tmp[abt_base_tmp["period"] == period][
        [
            "cid",
            "aid",
            "act_days",
            "act_paid_installments",
            "act_utl",
            "act_dueutl",
            "act_due",
            "act_age",
            "act_cc",
            "act_dueinc",
            "act_loaninc",
            "app_income",
            "app_loan_amount",
            "app_n_installments",
            "act_seniority",
            "app_nom_branch",
            "app_nom_gender",
            "app_nom_job_code",
            "app_number_of_children",
            "app_nom_marital_status",
            "app_nom_city",
            "app_nom_home_status",
            "app_nom_cars",
            "app_spendings",
            "fin_period",
            "status",
            "coll_status",
            "period",
            "act_cus_seniority",
            "act_cus_n_loans_hist",
            "act_cus_n_statC",
            "act_cus_n_statB",
            "act_cus_n_loans_act",
            "act_cus_utl",
            "act_cus_dueutl",
            "act_cus_cc",
        ]
    ]

    return abt_base


def make_summary_abt(period: int) -> pd.DataFrame:
    max_length: int = 12

    # read all abt_base tables since max_length months ago
    abt_base_current_period: pd.DataFrame = pd.read_csv(
        os.path.join(
            RUN_DATA_PATH,
            f"abt_base_{period}.csv",
        ),
    )
    cumulative_abt_base = pd.DataFrame(columns=abt_base_current_period.columns)
    for i in range(max_length - 1, -1, -1):
        requested_period = get_relative_period(period, -i)
        try:
            abt_base_tmp = pd.read_csv(
                os.path.join(
                    RUN_DATA_PATH,
                    f"abt_base_{requested_period}.csv",
                ),
            )
            cumulative_abt_base = pd.concat(
                [cumulative_abt_base, abt_base_tmp], ignore_index=True
            )
        except FileNotFoundError:
            print(f"File not found for period {requested_period}")
    # days=pay_days+15;
    # due=due_installments;
    cumulative_abt_base["Days"] = cumulative_abt_base["act_days"] + 15
    cumulative_abt_base["Due"] = cumulative_abt_base["act_due"]
    # CMax_Days is the max of days for a given cid across all the accounts(aid)
    cumulative_abt_base["CMax_Days"] = cumulative_abt_base.groupby(["cid", "period"])[
        "Days"
    ].transform("max")
    # CMax_Due is the max of due for a given cid across all the accounts(aid)
    cumulative_abt_base["CMax_Due"] = cumulative_abt_base.groupby(["cid", "period"])[
        "Due"
    ].transform("max")

    # Convert period to datetime
    period_date = datetime.strptime(str(period), "%Y%m")

    # Generate periods
    periods = [
        (period_date - relativedelta(months=i)).strftime("%Y%m")
        for i in range(max_length)
    ]
    # Variable definitions
    aggregated_variables = ["Due", "Days", "CMax_Days", "CMax_Due"]
    statistics = ["Mean", "Max", "Min"]
    lengths = [3, 6, 9, 12]

    # Initialize output DataFrame
    data_output = pd.DataFrame()

    # Process each row in the input data
    for _, row in abt_base_current_period.iterrows():
        # appropriate rows are ordered by period in ascending order
        abt_aid_rows: pd.DataFrame = cumulative_abt_base[
            cumulative_abt_base["aid"] == row["aid"]
        ]
        row_output = row.to_dict()
        row_output["act_n_arrears"] = abt_aid_rows[abt_aid_rows["Due"] > 0].shape[0]
        row_output["act_n_arrears_days"] = abt_aid_rows[
            abt_aid_rows["Days"] > 15
        ].shape[0]
        row_output["act_n_good_days"] = abt_aid_rows[
            (abt_aid_rows["Days"] > 0) & (abt_aid_rows["Days"] < 15)
        ].shape[0]
        row_output["act_n_cus_arrears"] = abt_aid_rows[
            abt_aid_rows["CMax_Due"] > 0
        ].shape[0]

        for length in lengths:
            # get last $length frows from abt_aid_rows
            last_length_rows = abt_aid_rows[
                abt_aid_rows["period"] >= get_relative_period(period, -length + 1)
            ]

            for variable in aggregated_variables:
                for statistic in statistics:
                    match statistic:
                        case "Mean":
                            agg_value = last_length_rows[variable].mean(skipna=True)
                        case "Max":
                            agg_value = last_length_rows[variable].max(skipna=True)
                        case "Min":
                            agg_value = last_length_rows[variable].min(skipna=True)
                        case _:
                            agg_value = np.nan

                    nmiss = sum(pd.isna(last_length_rows[variable]))
                    if nmiss != 0 or len(last_length_rows) != length:
                        row_output[f"agr{length}_{statistic}_{variable}"] = np.nan
                    else:
                        row_output[f"agr{length}_{statistic}_{variable}"] = agg_value
                    row_output[f"ags{length}_{statistic}_{variable}"] = agg_value
        # Append row output to the DataFrame
        data_output = pd.concat(
            [data_output, pd.DataFrame([row_output])], ignore_index=True
        )

    # normalize all columns
    normalized_data_output = data_output.copy()
    for column in data_output.columns:
        if column not in [
            "cid",
            "aid",
            "period",
            "status",
            "coll_status",
            "fin_period",
        ]:
            if data_output[column].nunique() == 1:
                normalized_data_output[column] = 0
            else:
                normalized_data_output[column] = (
                    data_output[column] - data_output[column].mean()
                ) / data_output[column].std()
            # fill missing values with 0
            normalized_data_output[column] = normalized_data_output[column].fillna(0)
    # save normalized data
    normalized_data_output.to_csv(
        os.path.join(
            RUN_DATA_PATH,
            f"abt_base_{period}_normalized.csv",
        ),
        index=False,
    )

    # Calculate scorem
    data_output["scorem"] = (
        1 * normalized_data_output["app_income"]
        + 1 * normalized_data_output["app_nom_branch"]
        + 1 * normalized_data_output["app_nom_gender"]
        + 2 * normalized_data_output["app_nom_job_code"]
        + 1 * normalized_data_output["app_number_of_children"]
        + 1 * normalized_data_output["app_nom_marital_status"]
        + 1 * normalized_data_output["app_nom_city"]
        + 1 * normalized_data_output["app_nom_home_status"]
        + 1 * normalized_data_output["app_nom_cars"]
    )

    # Calculate score
    data_output["score"] = (
        -1 * normalized_data_output.get("act_cus_utl", 0)
        - 1 * normalized_data_output.get("act_cus_dueutl", 0)
        - 1 * normalized_data_output.get("act_cus_cc", 0)
        - 1 * normalized_data_output.get("act_cus_n_loans_act", 0)
        + 3 * normalized_data_output.get("act_cus_seniority", 0)
        - 5 * normalized_data_output.get("act_cus_loan_number", 0)
        + 5 * (normalized_data_output.get("act_cus_loan_number", 0) == 1)
        + 6 * normalized_data_output.get("act_cus_n_statC", 0)
        - 3 * normalized_data_output.get("act_cus_n_statB", 0)
        + 1 * normalized_data_output["app_nom_branch"]
        + 3 * normalized_data_output["app_nom_gender"]
        + 6 * normalized_data_output["app_nom_job_code"]
        - 3
        * (
            (data_output["app_nom_job_code"] == 4)
            & (data_output["app_nom_marital_status"].isin([2, 3]))
            & (data_output["app_nom_gender"] == 1)
        )
        + 2
        * (
            (data_output["app_nom_job_code"] == 4)
            & (data_output["app_nom_marital_status"].isin([2, 3]))
            & (data_output["app_nom_gender"] == 0)
        )
        + 6 * normalized_data_output["app_number_of_children"]
        + 3 * normalized_data_output["app_nom_marital_status"]
        + 1 * normalized_data_output["app_nom_city"]
        + 1 * normalized_data_output["app_nom_home_status"]
        + 1 * normalized_data_output["app_nom_cars"]
        - 1 * normalized_data_output["app_spendings"]
        - 5 * normalized_data_output["act_days"]
        - 4 * normalized_data_output["act_utl"]
        - 6 * normalized_data_output["act_dueutl"]
        - 2 * normalized_data_output["act_due"]
        + 4 * normalized_data_output["act_age"]
        - 2 * normalized_data_output["act_cc"]
        - 1 * normalized_data_output["act_dueinc"]
        - 2 * normalized_data_output["act_loaninc"]
        + 2 * normalized_data_output["app_income"]
        - 1 * normalized_data_output["app_loan_amount"]
        - 4 * normalized_data_output["app_n_installments"]
        - 2 * normalized_data_output.get("agr3_Mean_Due", 0)
        - 3 * normalized_data_output.get("ags3_Mean_Days", 0)
        - 3 * normalized_data_output.get("agr6_Mean_Due", 0)
        - 3 * normalized_data_output.get("ags6_Mean_Days", 0)
        - 2 * normalized_data_output.get("agr9_Mean_Due", 0)
        - 3 * normalized_data_output.get("ags9_Mean_Days", 0)
        - 2 * normalized_data_output.get("agr12_Mean_Due", 0)
        - 3 * normalized_data_output.get("ags12_Mean_Days", 0)
        - 3 * normalized_data_output.get("ags3_Max_CMax_Due", 0)
        - 2 * normalized_data_output.get("ags12_Max_CMax_Due", 0)
        - 2 * normalized_data_output.get("ags9_Max_CMax_Days", 0)
        - 1 * normalized_data_output.get("act_n_cus_arrears", 0)
        - 2 * normalized_data_output.get("ags12_Max_CMax_Due", 0)
        + 5 * (normalized_data_output.get("ags12_Max_CMax_Due", 0) == 0)
    )

    # normalize score and scorem
    data_output["score"] = (
        data_output["score"] - data_output["score"].mean()
    ) / data_output["score"].std()
    data_output["scorem"] = (
        data_output["scorem"] - data_output["scorem"].mean()
    ) / data_output["scorem"].std()

    # score=sum(score,rannor(&seed)/2);
    # scorem=sum(scorem,rannor(&seed)/2);

    data_output["score"] = (
        data_output["score"] + np.random.normal(0, 1, len(data_output)) / 2
    )
    data_output["scorem"] = (
        data_output["scorem"] + np.random.normal(0, 1, len(data_output)) / 2
    )

    # Return the processed DataFrame
    return data_output
