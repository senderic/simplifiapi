import importlib.metadata
import logging

logging.getLogger("simplifiapi").setLevel(logging.INFO)

try:
    __version__ = importlib.metadata.version("simplifiapi")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.1"
