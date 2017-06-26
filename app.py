#!/usr/bin/env python
# encoding: utf-8
import os
import sys
import uuid
import logging
import logging.config
import random
import requests
from bottle import run, post

CONFIG = None
BACKUP_JOKES = None


# Production configuration
class Config(object):
    def __init__(self):
        """ Joke variables """
        self.JOKE_FILE = _get_config('BACKUP_JOKES', './jokes.txt')
        self.JOKE_URL = _get_config('JOKE_URL', 'https://icanhazdadjoke.com/')
        self.BIND_IP = _get_config('BIND_IP', '0.0.0.0')
        self.BIND_PORT = _get_config('BIND_PORT', 5000)

        """Logging Variables"""
        self.LOGGING_CONFIG = _get_logging_config()
        logging.config.dictConfig(self.LOGGING_CONFIG)
        self.LOGGER = logging.getLogger('dadjokes')


class InvalidConfigException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class NonBooleanStringException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def _get_config(key, default_value=None, required=False):
    """
    Gets config from environment variables
    Will return default_value if key is not in environment variables
    :param key: the key of the env variable you are looking for
    :param default_value: value to return if key not in os.environ.
    :param required: if true and key is not set, will raise InvalidConfigException
    :return: os.environ[key] if key in os.environ els default_value
    :exception InvalidConfigException - raised when a required config key is not properly set
    """
    if required and key not in os.environ:
        raise InvalidConfigException("Invalid ENV variable. Please check {0}".format(key))
    to_return = os.environ.get(key, default_value)
    if isinstance(to_return, basestring):
        try:
            to_return = _string_to_bool(to_return)
        except NonBooleanStringException:
            pass
    os.environ[key] = str(to_return)
    return to_return


def _get_logging_config():
    """
    returns a logging config Dict
    :return: Dict
    """

    _sys_log_handler_key = 'sys-logger6'
    _syslog_handler_config = {
                'class': 'logging.handlers.SysLogHandler',
                'address': '/dev/log',
                'facility': "local6",
                'formatter': 'verbose',
            }

    _file_handler_key = 'file-handler'
    _file_handler_config = {
                    "class": "logging.FileHandler",
                    "formatter": "verbose",
                    "filename": _get_config('LOG_FILE', '/tmp/dadjokes.log')
                }

    _base_logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(asctime)s - %(levelname)s %(module)s P%(process)d T%(thread)d %(message)s'
            },
        },
        'handlers': {
            'stdout': {
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
                'formatter': 'verbose',
            }

        },
        'loggers': {
            'dadjokes': {
                'handlers': ['stdout'],
                'level': _get_logging_level(),
                'propagate': True,
            },
        }
    }

    log_type = _get_config('LOG_TYPE', 'STDOUT').lower()

    to_return = _base_logging_config
    if log_type == 'syslog':
        to_return['handlers'][_sys_log_handler_key] = _syslog_handler_config
        to_return['loggers']['dadjokes']['handlers'].append('sys-logger6')
    if log_type == 'file':
        to_return['handlers'][_file_handler_key] = _file_handler_config
        to_return['loggers']['dadjokes']['handlers'].append('file-handler')

    return to_return


def _get_logging_level():
    """
    Converts our ENV variable HA_LOG_LEVEL to a logging level object
    :return: logging level object
    """
    _log_level = _get_config('LOG_LEVEL', 'info').lower()

    to_return = logging.INFO

    if _log_level == 'critical':
        to_return = logging.CRITICAL
    if _log_level == 'error':
        to_return = logging.ERROR
    if _log_level == 'warning':
        to_return = logging.WARNING
    if _log_level == 'debug':
        to_return = logging.DEBUG

    return to_return


def _string_to_bool(string):
    to_return = None
    if string.lower() in ('true', 't'):
        to_return = True
    if string.lower() in ('false', 'f'):
        to_return = False

    if to_return is None:
        raise NonBooleanStringException(string)

    return to_return


def _generate_csrf_token():
    """
    Generates a csrf token
    :return: String token
    """
    token = str(uuid.uuid4()) + str(uuid.uuid4())
    token = token.replace("-", "")
    return token


@post('/dadjoke')
def sharkfact():
    return _get_dadjoke(return_type='json')


def _get_dadjoke(return_type='text'):
    """
    Returns a random dad joke
    :param return_type: string, can be text for plaintext or json
    :return: Random dad joke
    """
    to_return = "Error! I can't find a dad joke for you :("
    _joke = _get_joke_online()

    if _joke is None:
        _joke = _get_backup_joke()

    if return_type.lower() == 'text':
        to_return = _joke
    if return_type.lower() == 'json':
        joke_json = {
            'response_type': 'in_channel',
            'text': _joke
        }
        to_return = joke_json

    return to_return


def _get_backup_joke():
    global BACKUP_JOKES

    return random.choice(BACKUP_JOKES)


def _get_joke_online():
    global CONFIG
    _return = None
    headers = {'User-Agent': 'curl/7.47.0'}
    response = requests.get(CONFIG.JOKE_URL, headers=headers)
    if response.status_code == 200:
        _return = response.text.strip()

    return _return


def _load_backup_jokes(file):
    """
    Loads backup jokes from a file
    :param file: String, path to file
    :return: none
    """
    global BACKUP_JOKES
    with open(file) as file_handler:
        BACKUP_JOKES = file_handler.readlines()

if __name__ == '__main__':
    CONFIG = Config()
    _load_backup_jokes(CONFIG.JOKE_FILE)
    run(host=CONFIG.BIND_IP, port=CONFIG.BIND_PORT)
