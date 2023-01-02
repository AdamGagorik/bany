import logging

from rich.console import Console


logger = logging.getLogger("pdf2ynab")
console = Console(force_terminal=True, width=1024)


def logline(level=logging.INFO, c="-", w=120):
    logger.log(level, c * w)
