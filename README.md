# BANY

A collection of scripts I've created to aid with budgeting using YNAB

# Setup

```bash
pyenv local 3.11.1
pipx install bany --python $(which python)
bany --help
```

## Create YNAB transactions from a PDF

### `cfgs/extract-pdf-sample.yaml`

- Define rules to match patterns in the text of a PDF
- Define the transactions to create from these matches

```yaml
# Regular Expressions defined for date like values
dates:
  Force Date:
    value: |-
      2023-01-01

  Check Date:
    regex: |-
      Check\s+Date\s+(?P<DATE>{MONTHS}\s+\d+,?\s+\d\d\d\d)

# Regular Expressions defined for money like values
amounts:
  401K:
    group: EARNINGS
    inflow: true
    regex: |-
      401K\s+
      (?P<HOURS>{NUMBER})\s+
      (?P<MONEY>{AMOUNT})\s+
      (?P<TOTAL>{AMOUNT})

  Salary:
    group: EARNINGS
    inflow: true
    regex: |-
      REGULAR\s+
      (?P<RATES>{NUMBER})\s+
      (?P<HOURS>{NUMBER})\s+
      (?P<MONEY>{AMOUNT})\s+
      (?P<TOTAL>{AMOUNT})

  TOTAL-EARNINGS:
    group: EARNINGS
    inflow: true
    total: true
    regex: |-
      Gross\s+Earnings\s+
      (?P<HOURS>{NUMBER})\s+
      (?P<MONEY>{AMOUNT})\s+
      (?P<TOTAL>{AMOUNT})

# Transactions to push to a YNAB budget (these may reference the matches defined above)
transactions:
- budget: 2023
  account: 'Checking'
  category: 'Internal Master Category: Inflow: Ready to Assign'
  payee: Company
  color: red
  amount: Salary
  date: Check Date

- budget: 2023
  account: 'Company'
  category: 'Investment: Fidelity'
  payee: 'Transfer : Fidelity : Syapse'
  memo: 2023
  color: yellow
  amount: 401K
  date: Check Date

```

### `bany extract pdf`

- Run the extact command to parse a PDF and upload transactions to YNAB

```bash
bany extract pdf --inp /path/to/pdf --config config.yaml
bany extract pdf --inp /path/to/pdf --config config.yaml --upload
```
