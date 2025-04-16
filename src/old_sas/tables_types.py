from typing import TypedDict
from old_sas.dictionaries import (
    Branch,
    Gender,
    JobCode,
    MaritalStatus,
    City,
    Homes,
    Cars,
    CollStat,
    Status,
)

ClientsRow = TypedDict(
    "ClientsRow",
    {
        "cid": str,
        "date_of_birth": str,
        "gender": Gender,
        "year": int,
        "job_code": JobCode,
        "number_of_children": int,
        "marital_status": MaritalStatus,
        "city": City,
        "home_status": Homes,
        "cars": Cars,
        "income": int,
        "spendings": int,
    },
)

AccountsRow = TypedDict(
    "AccountsRow",
    {
        "cid": str,
        "aid": str,
        "app_date": str,
        "period": int,
        "installment": int,
        "n_installments": int,
        "loan_amount": int,
        "branch": Branch,
    },
)

TransactionsRow = TypedDict(
    "TransactionsRow",
    {
        "cid": str,
        "aid": str,
        "period": int,
        "fin_period": int,
        "status": Status,
        "coll_status": CollStat,
        "due_installments": int,
        "paid_installments": int,
        "pay_days": int,
    },
)

CollectionActionsRow = TypedDict(
    "CollectionActionsRow",
    {
        "cid": str,
        "aid": str,
        "period": int,
        "action": str,
        "coll_status": CollStat,
    },
)

ProductionRow = TypedDict(
    "ProductionRow",
    {
        "aid": str,  # 16
        "cid": str,  # 10
        "app_date": str,
        "period": int,
        "date_of_birth": str,
        "installment": int,
        "n_installments": int,
        "loan_amount": int,
        "branch": Branch,
        "year": int,
        "gender": Gender,
        "age": int,
        "job_code": JobCode,
        "number_of_children": int,
        "marital_status": MaritalStatus,
        "city": City,
        "home_status": Homes,
        "cars": Cars,
        "income": int,
        "spendings": int,
    },
)

AbtBaseRow = TypedDict(
    "AbtBaseRow",
    {
        "cid": str,
        "aid": str,
        "period": int,
        "fin_period": int,
        "status": Status,
        "coll_status": CollStat,
        "act_days": int,
        "act_paid_installments": int,
        "act_utl": float,
        "act_dueutl": float,
        "act_due": float,
        "act_age": int,
        "act_cc": int,
        "act_dueinc": float,
        "act_loaninc": float,
        "app_income": int,
        "app_loan_amount": int,
        "app_n_installments": int,
        "act_seniority": int,
        "app_nom_branch": Branch,
        "app_nom_gender": Gender,
        "app_nom_job_code": JobCode,
        "app_number_of_children": int,
        "app_nom_marital_status": MaritalStatus,
        "app_nom_city": City,
        "app_nom_home_status": Homes,
        "app_nom_cars": Cars,
        "app_spendings": int,
        "act_cus_seniority": int,
        "act_cus_n_loans_hist": int,
        "act_cus_n_statC": int,
        "act_cus_n_statB": int,
        "act_cus_n_loans_act": int,
        "act_cus_utl": float,
        "act_cus_dueutl": float,
        "act_cus_cc": int,
    },
)
