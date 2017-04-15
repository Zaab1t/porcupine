import collections.abc
import contextlib
import functools
import json
import os

from porcupine import dirs


class InvalidValue(ValueError):
    """This is raised when attempting to set an invalid value."""


class _ConfigDict(collections.abc.MutableMapping):
    """A dictionary-like object that supports on-change callbacks.

    _ConfigDicts convert regular dicts into _ConfigDicts, and updates
    when attempting to replace an inner _ConfigDict with another
    mapping.

    >>> d = _ConfigDict()
    >>> d['test'] = {'a': 1}
    >>> d['test'] == {'a': 1}
    True
    >>> d['test'] = {'b': 2}
    >>> d['test'] == {'a': 1, 'b': 2}
    True
    """

    def __init__(self, *args, **kwargs):
        self._data = {}
        self._callbacks = collections.defaultdict(list)
        self._validators = collections.defaultdict(list)
        self.update(*args, **kwargs)   # convert dicts to _ConfigDicts

    def __repr__(self):
        return '<%s: %r>' % (type(self).__name__, self._data)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __setitem__(self, key, value):
        if isinstance(value, collections.abc.Mapping):
            if isinstance(self.get(key, None), _ConfigDict):
                self[key].update(value)
                return
            if not isinstance(value, _ConfigDict):
                value = _ConfigDict(value)

        for validator in self._validators[key]:
            if not validator(value):
                raise InvalidValue("invalid %s value %r" % (key, value))

        # object() is unequal to sane objects
        old_value = self.get(key, object())
        self._data[key] = value
        if old_value != value:
            for callback in self._callbacks[key]:
                callback(value)

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]

    def to_dict(self):
        result = {}
        for key, value in self.items():
            if isinstance(value, _ConfigDict):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result

    def connect(self, key, callback=None, *, run_now=True):
        """Run callback(value) when a value changes.

        If run_now is True, also run the callback immediately when this
        function is called.

        This function can also be used as a decorator:

            @some_config_dict.connect('key')
            def cool_callback(value):
                ...

                try:
                    # do some stuff
                finally:
                    config.disconnect('section', 'key', cool_callback)

        Or a context manager:

            def cool_callback():
                ...

            with some_config_dict.connect('key', cool_callback):
                # do some stuff
        """
        if callback is None:
            def decorator(real_callback):
                connect(key, real_callback, run_now=run_now)
                return real_callback
            return decorator

        @contextlib.contextmanager
        def disconnecter():
            try:
                yield
            finally:
                self.disconnect(key, callback)

        self._callbacks[key].append(callback)
        if run_now:
            callback(self.get(key))
        return disconnecter()

    def disconnect(self, key, callback):
        """Undo a connect() call."""
        _callbacks[key].remove(callback)

    def validator(self, key):
        """Add a validator function.

        The validator will be called before a value is set, and it should
        return True for valid values and False for invalid values.

        This should be used as a decorator:

            @some_callback_dict.validator('key')
            def validate_thingy(value):
                return value in [1, 2, 3]
        """
        def inner(callback):
            self._validators[key].append(callback)
            return callback
        return inner


# these contain only values that the user has changed
config = _ConfigDict()
_saved_config = {}

_config_file = os.path.join(dirs.configdir, 'config.json')
_default_theme_file = os.path.join(dirs.installdir, 'default_themes.ini')
_user_theme_file = os.path.join(dirs.configdir, 'themes.ini')


def load():
    assert not (config or _saved_config), "cannot load twice"

    try:
        with open(_config_file, 'r') as f:
            config.update(json.load(f))
    except FileNotFoundError:
        pass
    except (UnicodeError, OSError):
        log.exception("cannot read '%s'", _config_file)


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())
