import os
from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from old_sas.dictionaries import Status, CollStat
from old_sas.tables_types import AbtBaseRow
from other.util import get_relative_period, get_type


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
    period_datetime: datetime = datetime.strptime(str(period), "%Y%m")
    active_aids = transactions_df.loc[
        (transactions_df["status"] == Status.A) & (transactions_df["period"] == period),
        "aid",
    ]
    # Filter transactions for active accounts in the given period and earlier
    filtered_transactions = transactions_df[
        (transactions_df["aid"].isin(active_aids))
        & (transactions_df["period"] <= period)
    ]

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
            (period_datetime - datetime.strptime(row, "%Y-%m-%d")).days / 365.25
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
        lambda row: (datetime.strptime(str(row), "%Y%m") - period_datetime).days // 30
        + 1,
    )

    grouped_by_cid = abt_base_tmp.groupby(["cid"])

    abt_base_tmp["act_cus_n_loans_hist"] = grouped_by_cid["aid"].transform("count")

    abt_base_tmp["act_cus_n_statB"] = grouped_by_cid["status"].transform(
        lambda x: (x == Status.B).sum()
    )
    abt_base_tmp["act_cus_n_statC"] = grouped_by_cid["status"].transform(
        lambda x: (x == Status.C).sum()
    )
    abt_base_tmp["act_cus_n_loans_act"] = grouped_by_cid["aid"].transform("count")
    abt_base_tmp["act_cus_sum_installment"] = grouped_by_cid["installment"].transform(
        "sum"
    )
    abt_base_tmp["act_cus_sum_due"] = grouped_by_cid["due_installments"].transform(
        lambda x: (x > 0).sum()
    )
    abt_base_tmp["act_cus_sum_n_installments"] = grouped_by_cid[
        "n_installments"
    ].transform("sum")
    abt_base_tmp["act_cus_seniority"] = grouped_by_cid["act_seniority"].transform("max")
    abt_base_tmp["act_cus_utl"] = (
        abt_base_tmp["act_cus_sum_installment"]
        / abt_base_tmp["act_cus_sum_n_installments"]
    )
    abt_base_tmp["act_cus_dueutl"] = (
        abt_base_tmp["act_cus_sum_due"] / abt_base_tmp["act_cus_sum_n_installments"]
    )
    abt_base_tmp["act_cus_cc"] = (
        abt_base_tmp["act_cus_sum_installment"] + abt_base_tmp["spendings"]
    ) / abt_base_tmp["income"]

    renaming_dictionary: Dict[str, str] = {
        "branch": "app_nom_branch",
        "gender": "app_nom_gender",
        "job_code": "app_nom_job_code",
        "number_of_children": "app_number_of_children",
        "marital_status": "app_nom_marital_status",
        "city": "app_nom_city",
        "home_status": "app_nom_home_status",
        "cars": "app_nom_cars",
        "spendings": "app_spendings",
    }
    abt_base_tmp = abt_base_tmp.rename(columns=renaming_dictionary)

    relevant_columns: List[str] = [
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

    # Filter for the given period and select relevant columns
    abt_base = abt_base_tmp.loc[abt_base_tmp["period"] == period, relevant_columns]

    return abt_base


def make_summary_abt(period: int, data_path: str) -> pd.DataFrame:
    max_length: int = 12

    # read all abt_base tables since max_length months ago
    abt_base_current_period: pd.DataFrame = pd.read_csv(
        os.path.join(
            data_path,
            f"abt_base_{period}.csv",
        ),
        dtype=get_type(AbtBaseRow),
    )
    abt_bases: List[pd.DataFrame] = []
    for i in range(max_length - 1, -1, -1):
        requested_period = get_relative_period(period, -i)
        try:
            abt_base_tmp = pd.read_csv(
                os.path.join(
                    data_path,
                    f"abt_base_{requested_period}.csv",
                ),
                dtype=get_type(AbtBaseRow),
            )
            abt_bases.append(abt_base_tmp)
        except FileNotFoundError:
            print(f"File not found for period {requested_period}")
    cumulative_abt_base: pd.DataFrame = pd.concat(
        abt_bases, ignore_index=True, copy=False
    )
    # remove rows for accounts which does not appear in the current period
    cumulative_abt_base = cumulative_abt_base[
        cumulative_abt_base["aid"].isin(abt_base_current_period["aid"].unique())
    ]
    # days=pay_days+15;
    # due=due_installments;
    cumulative_abt_base["Days"] = cumulative_abt_base["act_days"] + 15
    cumulative_abt_base["Due"] = cumulative_abt_base["act_due"]
    # Calculate CMax_Days and CMax_Due as the max of Days and Due for a given cid across all accounts (aid)
    cumulative_abt_base[["CMax_Days", "CMax_Due"]] = cumulative_abt_base.groupby(
        ["cid", "period"]
    )[["Days", "Due"]].transform("max")

    # Variable definitions
    aggregated_variables = ["Due", "Days", "CMax_Days", "CMax_Due"]
    statistics = ["Mean", "Max", "Min"]
    lengths: List[int] = [3, 6, 9, 12]

    data_output: pd.DataFrame = abt_base_current_period
    print(data_output.shape)

    for length in sorted(lengths, reverse=True):
        rows_for_last_length = cumulative_abt_base.loc[
            cumulative_abt_base["period"] >= get_relative_period(period, -length + 1),
            ["aid", *aggregated_variables],
        ]
        grouped = rows_for_last_length.groupby(["aid"])[aggregated_variables]
        counts = grouped.transform("count")
        all_agr_variables_names = [
            f"agr{length}_{statistic}_{variable}"
            for variable in aggregated_variables
            for statistic in statistics
        ]
        all_ags_variables_names = [
            f"ags{length}_{statistic}_{variable}"
            for variable in aggregated_variables
            for statistic in statistics
        ]
        for statistic in statistics:
            agr_variables_names = [
                f"agr{length}_{statistic}_{variable}"
                for variable in aggregated_variables
            ]
            ags_variables_names = [
                f"ags{length}_{statistic}_{variable}"
                for variable in aggregated_variables
            ]
            match statistic:
                case "Mean":
                    means = grouped.transform("mean")
                    rows_for_last_length[agr_variables_names] = means
                    rows_for_last_length[ags_variables_names] = means.where(
                        counts >= length, np.nan
                    )
                case "Max":
                    # calculate max for the last $length periods for each aid
                    maxs = grouped.transform("max")
                    rows_for_last_length[agr_variables_names] = maxs
                    rows_for_last_length[ags_variables_names] = maxs.where(
                        grouped.transform("count") >= length, np.nan
                    )
                case "Min":
                    # calculate min for the last $length periods for each aid
                    mins = grouped.transform("min")
                    rows_for_last_length[agr_variables_names] = mins
                    rows_for_last_length[ags_variables_names] = mins.where(
                        grouped.transform("count") >= length, np.nan
                    )
                case _:
                    pass
        data_output = pd.merge(
            data_output,
            rows_for_last_length[
                ["aid", *all_agr_variables_names, *all_ags_variables_names]
            ].drop_duplicates(subset=["aid"]),
            on="aid",
            how="left",
        )

    # row_outputs: List[dict] = []

    cumulative_abt_base["act_n_arrears"] = (
        cumulative_abt_base[cumulative_abt_base["Due"] > 0]
        .groupby(["aid"])["Due"]
        .transform("count")
    )
    cumulative_abt_base["act_n_arrears"] = cumulative_abt_base["act_n_arrears"].fillna(
        0
    )
    cumulative_abt_base["act_n_arrears_days"] = (
        cumulative_abt_base[cumulative_abt_base["Days"] > 15]
        .groupby(["aid"])["Days"]
        .transform("count")
    )
    cumulative_abt_base["act_n_arrears_days"] = cumulative_abt_base[
        "act_n_arrears_days"
    ].fillna(0)
    cumulative_abt_base["act_n_good_days"] = (
        cumulative_abt_base[
            (cumulative_abt_base["Days"] > 0) & (cumulative_abt_base["Days"] < 15)
        ]
        .groupby(["aid"])["Days"]
        .transform("count")
    )
    cumulative_abt_base["act_n_good_days"] = cumulative_abt_base[
        "act_n_good_days"
    ].fillna(0)
    cumulative_abt_base["act_n_cus_arrears"] = (
        cumulative_abt_base[cumulative_abt_base["CMax_Due"] > 0]
        .groupby(["aid"])["CMax_Due"]
        .transform("count")
    )
    cumulative_abt_base["act_n_cus_arrears"] = cumulative_abt_base[
        "act_n_cus_arrears"
    ].fillna(0)

    # Process each row in the input data
    # for _, row in abt_base_current_period.iterrows():
    #     # appropriate rows are ordered by period in ascending order
    #     abt_aid_rows: pd.DataFrame = cumulative_abt_base[
    #         cumulative_abt_base["aid"] == row["aid"]
    #     ]
    #     row_output = row.to_dict()
    #     row_output["act_n_arrears"] = abt_aid_rows[abt_aid_rows["Due"] > 0].shape[0]
    #     row_output["act_n_arrears_days"] = abt_aid_rows[
    #         abt_aid_rows["Days"] > 15
    #     ].shape[0]
    #     row_output["act_n_good_days"] = abt_aid_rows[
    #         (abt_aid_rows["Days"] > 0) & (abt_aid_rows["Days"] < 15)
    #     ].shape[0]
    #     row_output["act_n_cus_arrears"] = abt_aid_rows[
    #         abt_aid_rows["CMax_Due"] > 0
    #     ].shape[0]

    #     for length in lengths:
    #         # get last $length frows from abt_aid_rows
    #         last_length_rows = abt_aid_rows[
    #             abt_aid_rows["period"] >= get_relative_period(period, -length + 1)
    #         ]

    #         for variable in aggregated_variables:
    #             for statistic in statistics:
    #                 match statistic:
    #                     case "Mean":
    #                         agg_value = last_length_rows[variable].mean(skipna=True)
    #                     case "Max":
    #                         agg_value = last_length_rows[variable].max(skipna=True)
    #                     case "Min":
    #                         agg_value = last_length_rows[variable].min(skipna=True)
    #                     case _:
    #                         agg_value = np.nan

    #                 nmiss = sum(pd.isna(last_length_rows[variable]))
    #                 if nmiss != 0 or len(last_length_rows) != length:
    #                     row_output[f"agr{length}_{statistic}_{variable}"] = np.nan
    #                 else:
    #                     row_output[f"agr{length}_{statistic}_{variable}"] = agg_value
    #                 row_output[f"ags{length}_{statistic}_{variable}"] = agg_value
    #     row_outputs.append(row_output)
    #     # Append row output to the DataFrame
    # data_output: pd.DataFrame = pd.DataFrame(row_outputs)

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
    # normalized_data_output.to_csv(
    #     os.path.join(
    #         data_path,
    #         f"abt_base_{period}_normalized.csv",
    #     ),
    #     index=False,
    # )

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
