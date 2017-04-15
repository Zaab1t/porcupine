import collections
import configparser
import contextlib
import logging
import tkinter.font as tkfont

log = logging.getLogger(__name__)


class InvalidValue(ValueError):
    """This is raised when validating a value fails."""


class _CallbackConfigParser(configparser.ConfigParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callbacks = collections.defaultdict(list)
        self._validators = collections.defaultdict(list)

    # currently all mutating methods call this, the documentation
    # describes this as "a custom, more complex interface, maintained
    # for backwards compatibility". the docstring says that this
    # "extends RawConfigParser.set by validating type and interpolation
    # syntax" so using it for this should be ok
    def set(self, section, option, value):
        for validator in self._validators[section, option]:
            if not validator(value):
                raise InvalidValue("validating %r failed" % (value,))

        # configparser uses strings for everything, so this treats '' as
        # equivalent to no value... kind of odd but it works
        old_value = self.get(section, option, fallback='')
        super().set(section, option, value)

        if old_value != str(value):
            for callback in self._callbacks[section, option]:
                callback(value)

    def validator(self, section, option):
        """Add a function that checks a value.

        Use this as a decorator, like this:

            @config.validator('the_section', 'something_positive')
            def _check_positive(value):
                return value > 0
        """
        def inner(callback):
            self._validators[section, option].append(callback)
            return callback

        return inner

    def connect(self, section, option, callback=None, *, run_now=True):
        """Run callback(value) when a configuration value changes.

        If run_now is True, also run the callback immediately when this
        function is called.

        This function can also be used as a decorator:

            @config.connect('section', 'option')
            def cool_callback(value):
                ...

            try:
                # do some stuff
            finally:
                config.disconnect('section', 'option', cool_callback)

        Or a context manager:

            def cool_callback():
                ...

            with config.connect('section', 'option', cool_callback):
                # do some stuff
        """
        if callback is None:
            def decorator(real_callback):
                self.connect(section, option, real_callback, run_now=run_now)
                return real_callback
            return decorator

        self._callbacks[section, option].append(callback)
        if run_now:
            # this doesn't support converters, but it's good enough
            callback(self.get(section, option))

        @contextlib.contextmanager
        def disconnecter():
            try:
                yield
            finally:
                self.disconnect(section, option, callback)
        return disconnecter()

    def disconnect(self, section, option, callback):
        """Undo a connect() call."""
        self._callbacks[section, option].remove(callback)

    # configparser.ConfigParser takes a converters keyword argument
    # starting with Python 3.5, but that's only for getting things on
    # new pythons, not setting things on old pythons. Booleans, strings
    # and floats are converted to strings automatically so they don't
    # need custom setters.

    # This font stuff only supports families and sizes because plugins
    # like highlight.py can do other things to the font later.
    def setfont(self, section, option, font):
        if not isinstance(font, tkfont.Font):
            font = tkfont.Font(font=font)
        string = json.dumps([font['family'], font['size']])
        self.set(section, option, string)

    def getfont(self, *args, **kwargs):
        family, size = json.loads(self.get(*args, **kwargs))
        return (family, size, '')   # tkinter accepts these font tuples


# the config contains only settings set by the user
config = _CallbackConfigParser(interpolation=None)
color_themes = configparser.ConfigParser(default_section='Default')

_config_file = os.path.join(dirs.configdir, 'config.json')
_default_theme_file = os.path.join(dirs.installdir, 'default_themes.ini')
_user_theme_file = os.path.join(dirs.configdir, 'themes.ini')


def load():
    config.read([_config_file])
    color_themes.read([_default_theme_file, _user_theme_file])
