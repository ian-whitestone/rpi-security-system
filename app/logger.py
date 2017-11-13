"""
Logger module used to create logging objects.
"""
import sys
import logging


DEFAULT_FORMAT = '%(asctime)s  - %(module)s - %(levelname)s - %(message)s'

def create_logger(name=None, log_level='INFO', log_format=DEFAULT_FORMAT,
                    log_filename=None):
    """Create a logging object.
    Args:
        name (str, optional): The name of the logger. Defaults to ``None``
        log_level (str, optional): The logging level. Defaults to ``INFO``
            Accepts: DEBUG, INFO, WARNING, ERROR, CRITICAL
        format (str, optional): Logging format. Defaults to
            ``%(asctime)s  - %(module)s - %(levelname)s - %(message)s``
        log_filename (str, optional): Filename to stream log to. Defaults to
            None and streams to sys.stdout
    Returns:
        logging.Logger: Logger object, configured with the passed in parameters.
    """
    level_map = {
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    if log_filename:
        logging.basicConfig(format=log_format,
            filename=log_filename)
    else:
        logging.basicConfig(format=log_format,
            stream=sys.stdout)

    log = logging.getLogger(name=name)
    logging.getLogger(name=name).setLevel(level_map[log_level])
    return log


# logging.getLogger("postgrez").setLevel(logging.WARNING)
