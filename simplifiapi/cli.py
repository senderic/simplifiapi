"""Command-line interface for simplifiapi.

Provides argument parsing, data export (JSON/CSV), token management,
and the main entry point that orchestrates authentication, data retrieval,
and file output.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any

import configargparse

from simplifiapi.client import Client

logger = logging.getLogger("simplifiapi")

JSON_FORMAT = "json"
CSV_FORMAT = "csv"
TOKEN_FILE = Path.home() / ".simplifiapi_token"


def _load_saved_token() -> str | None:
    """Load a previously saved token from disk.

    Returns:
        The token string if the file exists and is readable, ``None`` otherwise.
    """
    try:
        return TOKEN_FILE.read_text().strip() or None
    except (OSError, FileNotFoundError):
        return None


def _save_token(token: str) -> None:
    """Save a token to disk for later reuse.

    Args:
        token: The access token to persist.
    """
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)
    logger.warning(f"Token saved to {TOKEN_FILE}")


def parse_arguments(args: list[str]) -> configargparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Raw argument list (typically ``sys.argv[1:]``).

    Returns:
        Parsed namespace with attributes for credentials, data selectors,
        and output options.
    """
    parser = configargparse.ArgumentParser()

    parser.add_argument(
        "--email",
        nargs="?",
        default=None,
        help="The e-mail address for your Quicken Simplifi account",
    )
    parser.add_argument(
        "--password",
        nargs="?",
        default=None,
        help="The password for your Quicken Simplifi account",
    )
    parser.add_argument(
        "--token",
        nargs="?",
        default=None,
        help="Use existing token to bypass MFA check",
    )
    parser.add_argument(
        "--save-token",
        action="store_true",
        default=None,
        help="Save the authentication token to ~/.simplifiapi_token for reuse",
    )

    parser.add_argument(
        "--accounts", action="store_true", default=False, help="Retrieve accounts"
    )
    parser.add_argument(
        "--transactions",
        action="store_true",
        default=False,
        help="Retrieve transactions",
    )
    parser.add_argument(
        "--tags", action="store_true", default=False, help="Retrieve tags"
    )
    parser.add_argument(
        "--categories",
        action="store_true",
        default=False,
        help="Retrieve categories",
    )

    parser.add_argument(
        "--filename", default="output", help="Write results to file this prefix"
    )
    parser.add_argument(
        "--format",
        choices=[JSON_FORMAT, CSV_FORMAT],
        default=JSON_FORMAT,
        help="The format used to return data.",
    )

    return parser.parse_args(args)


def write_data(
    options: configargparse.Namespace, data: list[dict[str, Any]], name: str
) -> None:
    """Write retrieved data to a file.

    Args:
        options: Parsed CLI options (must have ``filename`` and ``format``).
        data: List of dicts representing retrieved records.
        name: Label used in the output filename (e.g. ``"accounts"``).

    Output filename pattern: ``{options.filename}_{name}.{options.format}``.

    CSV output handles nested dicts and lists by serializing them to JSON
    strings so they fit in a flat columnar format.
    """
    filename = f"{options.filename}_{name}.{options.format}"
    logger.warning(f"Saving {name} to {filename}")
    if options.format == CSV_FORMAT:
        if not data:
            logger.warning(f"No data to write for {name}")
            return
        fieldnames = list(
            dict.fromkeys(key for row in data if isinstance(row, dict) for key in row)
        )
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in data:
                if isinstance(row, dict):
                    flat = {}
                    for k, v in row.items():
                        flat[k] = json.dumps(v) if isinstance(v, (dict, list)) else v
                    writer.writerow(flat)
    elif options.format == JSON_FORMAT:
        with open(filename, "w+") as f:
            json.dump(data, f, indent=2)


def main() -> None:
    """Main entry point for the CLI.

    Orchestrates the full pipeline:
        1. Parse CLI arguments.
        2. Authenticate (token or email/password + optional MFA).
        3. Verify the token.
        4. Fetch the first dataset.
        5. Retrieve requested data types and write them to disk.
    """
    options = parse_arguments(sys.argv[1:])

    client = Client()

    token: str | None = options.token
    if not token:
        token = _load_saved_token()
    if not token:
        token = client.get_token(email=options.email, password=options.password)
        if token:
            logger.warning(f"Token: {token}")
            if options.save_token:
                _save_token(token)
        else:
            logger.error("Unable to retrieve token.")
            return
    elif options.save_token:
        _save_token(token)

    if not client.verify_token(token):
        logger.error("Unable to log in simplifi.")
        return

    datasets = client.get_datasets()
    if not datasets:
        logger.error("No datasets found.")
        return
    datasetId = datasets[0]["id"]

    if options.accounts:
        accounts = client.get_accounts(datasetId)
        write_data(options, accounts, "accounts")

    if options.transactions:
        transactions = client.get_transactions(datasetId)
        write_data(options, transactions, "transactions")

    if options.tags:
        tags = client.get_tags(datasetId)
        write_data(options, tags, "tags")

    if options.categories:
        categories = client.get_categories(datasetId)
        write_data(options, categories, "categories")
