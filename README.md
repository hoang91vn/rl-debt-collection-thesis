# RL Debt Collection

## Overview

RL Debt Collection is a project aimed at creating a robust and efficient system for managing and collecting debts using reinforcement learning techniques. The main loop runs in the **main.py** file, the decision making part is located in the **decision.py** file. The logic focuses around the _AccountPeriodInfo_ type, which contains the data for period based on the SAS-side **abt_x** (~state/observation), **transactions** and **collection_actions** tables. The decision function is able to access all the history of previous *AccountPeriodInfo*s through _accounts_histories_ by-aid dictionary.

## Installation

To install the project, clone the repository and install the required dependencies in your Python (version >= 3.10) virtual environment:

```bash
git clone https://github.com/akmere/rl-debt-collection.git
cd rl-debt-collection
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Usage

To run the project, execute the following command:

```bash
python python/main.py
```

## Common Issues

### Locks on SAS tables

Assure that you have closed all of your opened SAS tables (e.g. tables opened in SAS Enterprise Guide) to avoid LOCK errors.
