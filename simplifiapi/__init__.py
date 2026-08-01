"""Simplifiapi — an unofficial Python API and CLI for Quicken Simplifi.

Provides:
    - A :class:`Client` for programmatic access to Quicken Simplifi accounts,
      transactions, tags, and categories.
    - A CLI for exporting data to JSON or CSV files.

Example (Python API)::

    from simplifiapi.client import Client

    client = Client()
    token = client.get_token("user@example.com", "password")
    if client.verify_token(token):
        datasets = client.get_datasets()
        transactions = client.get_transactions(datasets[0]["id"])

Example (CLI)::

    $ simplifiapi --email user@example.com --password pass --transactions --format csv
"""

import importlib.metadata
import logging

logging.getLogger("simplifiapi").setLevel(logging.INFO)

try:
    __version__ = importlib.metadata.version("simplifiapi")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.1"
