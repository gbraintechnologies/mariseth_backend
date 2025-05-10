import logging
import os

from apps.shared.literals import APP_NAME


class ColoredLogger(logging.Logger):
    # ANSI escape codes for colors
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

    def __init__(self, name):
        super().__init__(name)
        # Add success level
        if not hasattr(logging, 'SUCCESS'):
            logging.SUCCESS = 25
            logging.addLevelName(logging.SUCCESS, 'SUCCESS')

    def success(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.SUCCESS):
            msg = f"{self.GREEN}{msg}{self.RESET}"
            self._log(logging.SUCCESS, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.INFO):
            msg = f"{self.BLUE}{msg}{self.RESET}"
            self._log(logging.INFO, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.WARNING):
            msg = f"{self.YELLOW}{msg}{self.RESET}"
            self._log(logging.WARNING, msg, args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.ERROR):
            msg = f"{self.RED}{msg}{self.RESET}"
            self._log(logging.ERROR, msg, args, **kwargs)


# Register our custom logger class
logging.setLoggerClass(ColoredLogger)

# Logging Configuration

LOGGERS = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['require_debug_true'],
            'formatter': 'verbose',
        },
        'null': {
            'class': 'logging.NullHandler',
        }
    },
    'loggers': {
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        APP_NAME: {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

logger = logging.getLogger(APP_NAME)
