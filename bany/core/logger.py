import logging

from rich.console import Console


logger = logging.getLogger("bany")
console = Console()


def logline(level=logging.INFO, c="-", w=120):
    logger.log(level, c * w)
