# BANY

A collection of scripts I've created to aid with budgeting using YNAB

# Setup

```bash
pipx install bany
```

## Create YNAB transactions from a PDF

### `config.yaml`

- Define rules to match patterns in the text of a PDF
- Define the transactions to create from these matches

```yaml
# Regular Expressions defined for date like values
dates:
  A:
    regex: "(?P<DATE>...)"

# Regular Expressions defined for money like values
amounts:
  B:
    regex: "(?P<TOTAL>...)"

# Transactions to push to a YNAB budget (these may reference the matches defined above)
transactions:
  budget: BudgetName
  account: AccountName
  category: CategoryName
  payee: PayeeName
  amount: A
  date: B
```

### `bany extract pdf`

- Run the extact command to parse a PDF and upload transactions to YNAB

```bash
bany extract pdf --inp /path/to/pdf --config config.yaml
bany extract pdf --inp /path/to/pdf --config config.yaml --upload
```
