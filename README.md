# simplifiapi

[![CI](https://github.com/senderic/simplifiapi/actions/workflows/ci.yml/badge.svg)](https://github.com/senderic/simplifiapi/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/senderic/simplifiapi/branch/main/graph/badge.svg)](https://codecov.io/gh/senderic/simplifiapi)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)

An unofficial Python API and CLI for [Quicken Simplifi](https://www.simplifimoney.com/), the personal finance platform. Export your accounts, transactions, tags, and categories to JSON or CSV.

- **[Documentation](https://ericsender.com/simplifiapi/docs/)**
- **[Brochure site](https://ericsender.com/simplifiapi/)**

---

## Quick Start

```bash
# Install from GitHub
pip install git+https://github.com/senderic/simplifiapi

# Export transactions as CSV
simplifiapi --email you@example.com --password yourpass --transactions --format csv

# Or use an existing token to skip MFA
simplifiapi --token "your-token-here" --accounts --transactions --tags --categories
```

If MFA is enabled on your account, you'll be prompted for the code after entering your password.

---

## Python API

```python
from simplifiapi.client import Client

client = Client()

# Authenticate — MFA is handled interactively if needed
token = client.get_token("you@example.com", "yourpass")
if token and client.verify_token(token):
    datasets = client.get_datasets()
    ds_id = datasets[0]["id"]

    transactions = client.get_transactions(ds_id)
    accounts = client.get_accounts(ds_id)

    for txn in transactions:
        print(f"{txn['description']}: ${txn['amount']}")
```

---

## CLI Reference

```
simplifiapi [-h] [--email [EMAIL]] [--password [PASSWORD]] [--token [TOKEN]]
            [--accounts] [--transactions] [--tags] [--categories]
            [--filename FILENAME] [--format {json,csv}]
```

| Flag | Description |
|------|-------------|
| `--email` | Simplifi account email |
| `--password` | Simplifi account password |
| `--token` | Bypass login by providing an existing token |
| `--accounts` | Retrieve accounts |
| `--transactions` | Retrieve transactions |
| `--tags` | Retrieve tags |
| `--categories` | Retrieve categories |
| `--filename` | Output file prefix (default: `output`) |
| `--format` | Output format: `json` or `csv` (default: `json`) |

### Examples

```bash
# All data as JSON
simplifiapi --email you@example.com --password pass --accounts --transactions --tags --categories

# Transactions only, CSV output with custom filename
simplifiapi --token abc123 --transactions --filename march2024 --format csv

# Accounts only, JSON (default)
simplifiapi --token abc123 --accounts
```

Output filenames follow the pattern `{filename}_{type}.{format}`. For example:

- `output_accounts.json`
- `march2024_transactions.csv`

---

## CSV Output

Nested fields (dicts or lists) are serialized to JSON strings within the CSV columns, preserving all data in a flat format.

For full-fidelity exports, use JSON format (`--format json`).

---

## Development

```bash
git clone git@github.com:senderic/simplifiapi.git
cd simplifiapi
pip install -e ".[dev]"

# Run tests
pytest --cov=simplifiapi -v

# Lint
ruff check simplifiapi/ tests/
ruff format --check simplifiapi/ tests/
```

---

## Authentication

Simplifi uses OAuth 2.0 with multi-factor authentication (MFA). The `get_token()` method:

1. Sends email/password to the authorize endpoint.
2. If MFA is required, prompts for the code via stdin.
3. Exchanges the authorization code for an access token.
4. Returns the token, which you can cache and reuse with `--token` or `verify_token()`.

---

## Thanks

This library is heavily inspired by [mintapi](https://github.com/mintapi/mintapi).

---

## License

MIT. See [LICENSE](LICENSE).
