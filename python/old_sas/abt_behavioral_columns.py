import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta


def make_abt(data_input, period, max_length=12):
    # Convert period to datetime
    period_date = datetime.strptime(period, "%Y%m")

    # Generate periods
    periods = [
        (period_date - relativedelta(months=i)).strftime("%Y%m")
        for i in range(max_length)
    ]
    n_periods = len(periods)
    first_period = periods[-1]

    # Calculate index
    index = (period_date.year - int(first_period[:4])) * 12 + (
        period_date.month - int(first_period[4:])
    )

    # Variable definitions
    var_agr = ["Due", "Days", "CMax_Days", "CMax_Due"]
    n_var_agr = len(var_agr)
    sagr = ["Mean", "Max", "Min"]
    n_sagr = len(sagr)
    lengths = [3, 6, 9, 12]
    n_lengths = len(lengths)

    # Initialize output DataFrame
    data_output = pd.DataFrame()

    # Process each row in the input data
    for _, row in data_input.iterrows():
        row_output = {}

        for length in lengths:
            first_index = max(0, index - length + 1)

            for v in var_agr:
                for a in sagr:
                    values = [
                        row.get(f"{v}_{periods[i]}", np.nan)
                        for i in range(first_index, index + 1)
                    ]
                    if a == "Mean":
                        agg_value = np.nanmean(values)
                    elif a == "Max":
                        agg_value = np.nanmax(values)
                    elif a == "Min":
                        agg_value = np.nanmin(values)
                    else:
                        agg_value = np.nan

                    nmiss = sum(pd.isna(values))
                    row_output[f"agr{length}_{a}_{v}"] = (
                        agg_value if nmiss <= 1 else ".m"
                    )
                    row_output[f"ags{length}_{a}_{v}"] = agg_value

        # Additional aggregations
        first_index = max(0, index - lengths[-1] + 1)  # Ensure first_index is defined
        row_output["act_n_arrears"] = sum(
            row.get(f"due_{periods[i]}", 0) >= 1 for i in range(first_index, index + 1)
        )
        row_output["act_n_arrears_days"] = sum(
            row.get(f"days_{periods[i]}", 0) > 15 for i in range(first_index, index + 1)
        )
        row_output["act_n_good_days"] = sum(
            0 < row.get(f"days_{periods[i]}", 0) < 15
            for i in range(first_index, index + 1)
        )
        row_output["act_n_cus_arrears"] = sum(
            row.get(f"CMax_Due_{periods[i]}", 0) >= 1
            for i in range(first_index, index + 1)
        )

        # Append row output to the DataFrame
        data_output = pd.concat(
            [data_output, pd.DataFrame([row_output])], ignore_index=True
        )

    # Return the processed DataFrame
    return data_output
