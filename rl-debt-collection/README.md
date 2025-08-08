# RL Debt Collection

## Overview

RL Debt Collection is a project aimed at creating a simulator of debt collection processes. It enables users via **run** function to perform simulation customized mainly be providing **choose_actions** and **simulate_reactions** argument functions. It could find its applications in testing solutions aimed at optimizing the process and maximizing profit. Each simulation generates data in the form of csv files, **abt_base\_{period}.csv**, **summary_abt\_{period}.csv**, **collection_actions.csv**, **transactions.csv**, **clients.csv**. They can be used later by the injected user solution mainly by collecting data about effectiveness, valuing previous decisions and taking the new ones.

## Tables

### abt_base\_{period}.csv

Basic data of given account and client for a given period.

### summary_abt\_{period}.csv

Basic data extended with summary data e.g. agr6_Mean_Due, mean number of due installments over the last 6 periods. ags{x}\_ differ from agr{x}\_ by being NaN when not all data over the last x periods is available.

### collection_actions.csv

Table of all collection actions.

### transactions.csv

Table of all transactions.

## Tests

RL Debt Collection uses **pytest** library to perform testing. Tests are located in _tests_ directory and can be executed using `uv run pytest` command.

## Prerequisites

- uv >= 0.8.0
- Python >= 3.10
