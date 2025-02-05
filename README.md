# RL Debt Collection

## Overview

RL Debt Collection is a project aimed at creating a robust and efficient system for managing and collecting debts using reinforcement learning techniques.

## Installation

To install the project, clone the repository and install the required dependencies in your Python virtual environment:

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
python main.py
```

## Common Issues

### Locks on SAS tables

Assure that you have closed all of your opened SAS tables (e.g. tables opened in SAS Enterprise Guide) to avoid LOCK errors.
