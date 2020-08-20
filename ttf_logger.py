import logging
import logging.config
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler
from functools import wraps

logging.config.fileConfig('ttf_logging.conf')

debug_logger = logging.getLogger('DEBUG_LOGGER')
error_logger = logging.getLogger('ERROR_LOGGER')
stock_logger = logging.getLogger('STOCK_LOGGER')

"""
def error_logging(function):

    global error_logger
    name = function.__name__

    @wraps(function)
    def wrapper(*args, **kwargs):

        try:
            result = function(*args, *kwargs)
        except Exception:
            error_logger.error("{} produced an error: ".format(name),
                                exc_info=True)
            return function(*args, **kwargs)

        return result
    
    return wrapper
"""