"""Entry point for running the package as a module.

Usage::

    python -m simplifiapi --accounts --format csv
"""

import logging

from simplifiapi.cli import main

logging.getLogger("simplifiapi").setLevel(logging.INFO)

if __name__ == "__main__":
    main()
