from typing import Any, Dict, Literal, TypedDict, cast, Self, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math
from .dictionaries import (
    MaritalStatus,
    Branch,
    Cars,
    City,
    CollStat,
    Gender,
    Homes,
    JobCode,
)
from .tables_types import ClientsRow


class Client:
    cid: str
    date_of_birth: str
    gender: Gender
    year: int
    job_code: JobCode
    number_of_children: int
    marital_status: MaritalStatus
    city: City
    home_status: Homes
    cars: Cars
    income: int
    spendings: int

    def __init__(
        self,
        data: ClientsRow,
    ):
        self.cid = data["cid"]
        self.date_of_birth = data["date_of_birth"]
        self.gender = Gender(data["gender"])
        self.marital_status = MaritalStatus(data["marital_status"])
        self.job_code = JobCode(data["job_code"])
        self.home_status = Homes(data["home_status"])
        self.city = City(data["city"])
        self.cars = Cars(data["cars"])
        self.number_of_children = data["number_of_children"]
        self.income = data["income"]
        self.spendings = data["spendings"]
        self.year = data["year"]

    def get_age(self) -> int:
        return self.year - datetime.strptime(self.date_of_birth, "%Y-%m-%d").year

    @staticmethod
    def get_starter(
        cid: str,
        generator: np.random.Generator,
        n_term_vars: int,
        current_date: datetime,
    ) -> "Client":
        pr: float = (
            0.01
            + (
                1.5
                + np.sin(n_term_vars * math.pi * 1 / n_term_vars)
                + generator.random() / 5
            )
            / 8
        ) / 0.36
        age: int = int(
            (75 - 18) * (generator.random() + 4) / 7
            + 10
            + 20 * generator.random()
            + 5 * pr
        )
        age = max(18, min(age, 75))
        date_of_birth: datetime = current_date - timedelta(days=age * 365)
        date_of_birth_str: str = date_of_birth.strftime("%Y-%m-%d")

        client: Client = Client(
            ClientsRow(
                cid=cid,
                cars=Cars.NO,
                city=City(int(generator.random() * 3 + 1.5)),
                date_of_birth=date_of_birth_str,
                gender=cast(
                    Gender,
                    max(0, min(int(generator.random() > (0.45 + pr / 20)), 1)),
                ),
                home_status=Homes(int(generator.random() * 2 + 1.5)),
                job_code=JobCode.CONTRACT
                if generator.random() < 0.4
                else JobCode.OWNER_COMPANY,
                marital_status=MaritalStatus.SINGLE,
                number_of_children=0,
                income=0,
                spendings=0,
                year=(date_of_birth + timedelta(days=365 * 18)).year,
            )
        )
        client.refresh_income_and_spendings(generator)
        while client.year < current_date.year:
            client.simulate_next_year(generator)
            client.refresh_income_and_spendings(generator)
        return client

    def refresh_income_and_spendings(self, generator: np.random.Generator):
        if self.job_code == JobCode.PERMANENT:
            self.income = int(
                (7000 - 1500) * abs(generator.standard_normal()) / 4 + 1500
            )
        elif self.job_code == JobCode.RETIRED:
            self.income = int((4000 - 300) * abs(generator.standard_normal()) / 4 + 300)
        elif self.job_code == JobCode.OWNER_COMPANY:
            self.income = int(
                (17000 - 3000) * abs(generator.standard_normal()) / 4 + 3000
            )
        else:  # JobCode.CONTRACT or other
            self.income = int((5000 - 500) * abs(generator.standard_normal()) / 4 + 500)

        self.spendings = int(
            20
            * self.income
            * (
                abs(generator.standard_normal())
                + self.home_status.value
                + self.cars.value
                - 2
            )
            / (8 * 20)
        )

    def simulate_next_year(
        self,
        generator: np.random.Generator,
    ):
        self.year = self.year + 1
        age: int = self.get_age()
        if (
            self.marital_status == MaritalStatus.SINGLE
            and age < 60
            and generator.random() < 0.1
        ):
            self.marital_status = MaritalStatus.MARRIED
        if (
            self.number_of_children < 1
            and self.marital_status == MaritalStatus.MARRIED
            and generator.random() < 0.1
            and age < 45
        ):
            self.number_of_children += 1
        if (
            self.number_of_children == 1
            and self.marital_status == MaritalStatus.MARRIED
            and generator.random() < 0.05
            and age < 45
        ):
            self.number_of_children += 1
        if (
            self.number_of_children == 2
            and self.marital_status == MaritalStatus.MARRIED
            and generator.random() < 0.01
            and age < 45
        ):
            self.number_of_children += 1
        if self.number_of_children > 0 and age > 45 and generator.random() < 0.1:
            self.number_of_children -= 1
        if self.marital_status == MaritalStatus.MARRIED and generator.random() < 0.01:
            self.marital_status = MaritalStatus.DIVORCED
        if (
            self.marital_status == MaritalStatus.MARRIED
            and age > 60
            and generator.random() < 0.1
        ):
            self.marital_status = MaritalStatus.WIDOWED

        if (
            (
                self.marital_status in [MaritalStatus.MARRIED, MaritalStatus.SINGLE]
                or age > 25
            )
            and self.home_status == Homes.WITH_PARENTS
            and generator.random() < 0.7
        ):
            self.home_status = Homes.RENTAL
        if (
            (
                self.marital_status in [MaritalStatus.MARRIED, MaritalStatus.SINGLE]
                or age > 25
            )
            and self.home_status == Homes.WITH_PARENTS
            and generator.random() < 0.2
        ):
            self.home_status = Homes.OWNER
        if self.home_status == Homes.RENTAL and generator.random() < 0.05:
            self.home_status = Homes.OWNER
        if generator.random() < 0.005:
            self.city = City(max(1, min(int(generator.random() * 3 + 1.5), 4)))
        if self.cars == Cars.NO and 20 < age <= 60 and generator.random() < 0.05:
            self.cars = Cars.OWNER
        if self.cars == Cars.OWNER and generator.random() < 0.001:
            self.cars = Cars.NO
        if self.job_code != JobCode.RETIRED and age > 50 and generator.random() < 0.1:
            self.job_code = JobCode.RETIRED
        if self.job_code != JobCode.RETIRED and age > 70:
            self.job_code = JobCode.RETIRED
        if self.job_code == JobCode.CONTRACT and generator.random() < 0.05:
            self.job_code = JobCode.PERMANENT
        if (
            self.job_code in [JobCode.PERMANENT, JobCode.CONTRACT]
            and generator.random() < 0.01
        ):
            self.job_code = JobCode.OWNER_COMPANY
        if self.job_code == JobCode.OWNER_COMPANY and generator.random() < 0.01:
            self.job_code = JobCode.PERMANENT
        if (
            self.job_code in [JobCode.PERMANENT, JobCode.OWNER_COMPANY]
            and generator.random() < 0.005
        ):
            self.job_code = JobCode.CONTRACT
        self.refresh_income_and_spendings(generator)

    def to_series(self) -> pd.Series:
        return pd.Series(
            {
                "cid": self.cid,
                "date_of_birth": self.date_of_birth,
                "gender": self.gender.value,
                "marital_status": self.marital_status.value,
                "job_code": self.job_code.value,
                "home_status": self.home_status.value,
                "city": self.city.value,
                "cars": self.cars.value,
                "number_of_children": self.number_of_children,
                "income": self.income,
                "spendings": self.spendings,
                "year": self.year,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cid": self.cid,
            "date_of_birth": self.date_of_birth,
            "gender": self.gender.value,
            "marital_status": self.marital_status.value,
            "job_code": self.job_code.value,
            "home_status": self.home_status.value,
            "city": self.city.value,
            "cars": self.cars.value,
            "number_of_children": self.number_of_children,
            "income": self.income,
            "spendings": self.spendings,
            "year": self.year,
        }

    @staticmethod
    def get_list_from_dataframe(df: pd.DataFrame) -> List["Client"]:
        return [
            Client(ClientsRow(**{str(k): v for k, v in row.items()}))
            for row in df.reset_index().to_dict(orient="records", index=True)
        ]


class Account:
    aid: str
    cid: str
    app_date: str
    period: str
    installment: float
    n_installments: int
    loan_amount: float
    branch: Branch

    def __init__(
        self,
        aid: str,
        cid: str,
        app_date: str,
        period: str,
        installment: float,
        n_installments: int,
        loan_amount: float,
        branch: Branch,
    ):
        self.aid = aid
        self.cid = cid
        self.app_date = app_date
        self.period = period
        self.installment = installment
        self.n_installments = n_installments
        self.loan_amount = loan_amount
        self.branch = branch

    @staticmethod
    def generate_account(
        client: Client,
        aid: str,
        app_date: datetime,
        generator: np.random.Generator,
    ) -> "Account":
        # period has format YYYYMM
        period: str = app_date.strftime("%Y%m")
        app_date_str: str = app_date.strftime("%Y-%m-%d")
        pr: float = (
            0.01 + (1.5 + np.sin(1 * math.pi * 1 / 1) + generator.random() / 5) / 8
        ) / 0.36
        installment: int = int(abs(generator.standard_normal()) * 200 + 60 + 50 * pr)
        # Determine the number of installments based on probabilities
        if generator.random() < (0.2 - pr / 50):
            n_installments: int = 36
        elif generator.random() < (0.3 + pr / 50):
            n_installments = 24
        else:
            n_installments = 12
        loan_amount: float = n_installments * installment
        # Calculate branch value with adjustments
        branch_value = int(generator.random() * 3 + 1.5 + pr / 10)
        # Clamp branch value between 1 and 4
        branch_value = max(1, min(branch_value, 4))
        branch: Branch = Branch(branch_value)
        return Account(
            aid=aid,
            cid=client.cid,
            app_date=app_date_str,
            period=period,
            installment=installment,
            n_installments=n_installments,
            loan_amount=loan_amount,
            branch=branch,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aid": self.aid,
            "cid": self.cid,
            "app_date": self.app_date,
            "period": self.period,
            "installment": self.installment,
            "n_installments": self.n_installments,
            "loan_amount": self.loan_amount,
            "branch": self.branch.value,
        }


seed: int = 123456789
generator: np.random.Generator = np.random.default_rng(seed=seed)
