"""Setting manager for Porcupine."""

import codecs
import collections
import configparser
import contextlib
import json
import logging
import os

from porcupine import dirs


log = logging.getLogger(__name__)

_config = {}      # contains only non-default settings
_default_config = {}
_saved_config = {}

# these are {(section, key): value}
_callbacks = collections.defaultdict(list)
_validators = collections.defaultdict(list)

color_themes = configparser.ConfigParser(default_section='Default')

_config_file = os.path.join(dirs.configdir, 'config.json')
_default_theme_file = os.path.join(dirs.installdir, 'default_themes.ini')
_user_theme_file = os.path.join(dirs.configdir, 'themes.ini')


class InvalidValue(ValueError):
    """This is raised when attempting to set an invalid value."""


def get(section, key):
    try:
        return _config[section][key]
    except KeyError:
        return _default_config[section][key]


# yes, this conflicts with a builtin
# i'm evil xDD MUHAHAHAHAAA!!
def set(section, key, value):
    old_value = get(section, key)
    if value == old_value:
        # this might cause some problems, e.g. replacing 1 with 1.0
        # doesn't work, but currently it's not a problem
        return

    for validator in _validators[section, key]:
        if not validator(value):
            raise InvalidValue("invalid %s value %r" % (key, value))

    if value == _default_config[section][key]:
        # use the default instead
        del _config[section][key]
        if not _config[section]:
            # last key
            del _config[section]
    else:
        try:
            _config[section][key] = value
        except KeyError:
            # first key
            _config[section] = {key: value}

    for callback in _callbacks[section, key]:
        callback(value)


def add_key(section, key, default_value):
    try:
        _default_config[section][key] = default_value
    except KeyError:
        # new section
        _default_config[section] = {key: default_value}


def connect(section, key, callback=None, *, run_now=True):
    """Run callback(value) when a configuration value changes.

    If run_now is True, also run the callback immediately when this
    function is called.

    This function can also be used as a decorator:

        @config.connect('section', 'key')
        def cool_callback(value):
            ...

        try:
            # do some stuff
        finally:
            config.disconnect('section', 'key', cool_callback)

    Or a context manager:

        def cool_callback():
            ...

        with config.connect('section', 'key', cool_callback):
            # do some stuff
    """
    if callback is None:
        def decorator(real_callback):
            connect(section, key, real_callback, run_now=run_now)
            return real_callback

        return decorator

    @contextlib.contextmanager
    def disconnecter():
        try:
            yield
        finally:
            disconnect(section, key, callback)

    _callbacks[section, key].append(callback)
    if run_now:
        callback(get(section, key))
    return disconnecter()


def disconnect(section, key, callback):
    """Undo a connect() call."""
    _callbacks[section, key].remove(callback)


def validator(section, key):
    """Add a validator function.

    The validator will be called before a value is set, and it should
    return True for valid values and False for invalid values.

    This should be used as a decorator:

        @config.validator('section', 'key')
        def validate_thingy(value):
            return value in [1, 2, 3]
    """
    def inner(callback):
        _validators[section, key].append(callback)
        return callback

    return inner


def load():
    # these must be read first because config's editing:color_theme
    # validator needs it
    color_themes.read([_default_theme_file, _user_theme_file])

    _saved_config.clear()
    try:
        with open(_config_file, 'r') as f:
            _saved_config.update(json.load(f))
    except FileNotFoundError:
        pass
    except (UnicodeError, OSError):
        log.exception("cannot read '%s'", _config_file)

    for section, sub in _saved_config.items():
        for key, value in sub.items():
            try:
                set(section, key, value)
            except InvalidValue:
                log.warning("invalid %s:%s value %r, using %r instead",
                            section, key, value, get(section, key))


def save():
    # It's important to check if the config changed because otherwise:
    #  1. The user opens up two Porcupines. Let's call them A and B.
    #  2. The user changes settings in porcupine A.
    #  3. The user closes Porcupine A and it saves the settings.
    #  4. The user closes Porcupine B and it overwrites the settings
    #     that A saved.
    #  5. The user opens up Porcupine again and the settings are gone.
    #
    # Of course, this doesn't handle the user changing settings in
    # both Porcupines, but I think it's not too bad to assume that
    # most users don't do that.
    if _config == _saved_config:
        log.info("config hasn't changed, not saving it")
    else:
        log.info("saving config to '%s'", _config_file)
        with open(_config_file, 'w') as file:
            json.dump(_config, file, indent=4)
            file.write('\n')


def reset():
    for section, sub in _default_config.items():
        for key, value in sub.items():
            set(section, key, value)


# some of this setup stuff is done here because multiple porcupine
# modules use these values
add_key('general', 'encoding', 'UTF-8')
add_key('general', 'color_theme', 'Default')
add_key('general', 'window_size', [650, 500])  # must not be modified in-place


# running porcupine on different python versions with the same setting
# file can screw this up
@validator('general', 'encoding')
def _validate_encoding(name):
    try:
        codecs.lookup(name)
        return True
    except LookupError:
        return False


# must not break if the user deletes a custom color theme
@validator('general', 'color_theme')
def _validate_color_theme(name):
    return name in color_themes
