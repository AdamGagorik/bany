import logging

logger = logging.getLogger("bany")


def logline(level=logging.INFO, c="-", w=120):
    logger.log(level, c * w)
