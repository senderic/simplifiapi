import csv
import json
import logging
import sys
from typing import Any

import configargparse

from simplifiapi.client import Client

logger = logging.getLogger("simplifiapi")

JSON_FORMAT = "json"
CSV_FORMAT = "csv"


def parse_arguments(args: list[str]) -> configargparse.Namespace:
    parser = configargparse.ArgumentParser()

    # Credential
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

    # Datasets
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
        "--categories", action="store_true", default=False, help="Retrieve categories"
    )

    # Export
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
    options = parse_arguments(sys.argv[1:])

    client = Client()

    token: str | None = options.token
    if not token:
        token = client.get_token(email=options.email, password=options.password)
        if not token:
            logger.error("Unable to retrieve token.")
            return

    if not client.verify_token(token):
        logger.error("Unable to log in simplifi.")
        return

    # Retrieve first dataset
    # TODO: Support multiple datasets
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
