class InvalidValue(ValueError):
    """This is raised when attempting to set an invalid value."""


config = {}     # {sectionname: section}


class _Section:

    def __init__(self):
        self._defaults = {}
        self._user_values = {}
        self._saved_user_values = None   # will be set by load()
        self._callbacks = collections.defaultdict(list)
        self._validators = collections.defaultdict(list)

    def __getitem__(self, key):
        try:
            return self._user_values[key]
        except KeyError:
            return self._defaults[key]

    def __setitem__(self, key, value):
        try:
            if self[key] == value:
                # this might cause some problems, e.g. replacing 1 with
                # 1.0 doesn't work, but currently this is good enough
                return
        except KeyError:
            # gotta allow unknown keys too, makes mixing different
            # porcupine versions and plugins easier
            self._user_values[key] = value
            return

        for validator in self._validators[key]:
            if not validator(value):
                raise InvalidValue("invalid %s value %r" % (key, value))

        if value == self._defaults[key]:
            # use the default instead and delete empty sections
            del self._user_values[key]
        else:
            self._user_values[key] = value

        for callback in self._callbacks[key]:
            callback(value)

    def add_key(self, key, default_value):
        self._defaults[key] = default_value

    def connect(self, key, callback=None, *, run_now=True):
        """Run callback(value) when a configuration value changes.

        If run_now is True, also run the callback immediately when this
        function is called.

        This function can also be used as a decorator:

            @some_section.connect('key')
            def cool_callback(value):
                ...

                try:
                    # do some stuff
                finally:
                    some_section.disconnect('key', cool_callback)

        Or a context manager:

            def cool_callback():
                ...

            with some_section.connect('key', cool_callback):
                # do some stuff
        """
        if callback is None:
            def decorator(real_callback):
                self.connect(key, real_callback, run_now=run_now)
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
            callback(self[key])
        return disconnecter()

    def validator(self, section, key):
        """Add a validator function.

        The validator will be called before a value is set, and it
        should return True for valid values and False for invalid
        values.

        This should be used as a decorator:

            @some_section.validator('key')
            def validate_thingy(value):
                return value in [1, 2, 3]
        """
        def inner(callback):
            self._validators[section, key].append(callback)
            return callback
        return inner

    def reset(self):
        # this is like self._user_values.clear(), but runs callbacks
        for key, default in self._defaults.items():
            self[key] = default

        # if there's something left it's from other porcupine versions
        # with more config keys, and this porcupine has no callbacks
        self._user_values.clear()

    # dict(self) uses this
    def keys(self):
        return self._defaults.keys()


def load():
    saved_config = {}
    try:
        with open(_config_file, 'r') as f:
            saved_config.update(json.load(f))
    except FileNotFoundError:
        pass
    except (UnicodeError, OSError):
        log.exception("cannot read '%s'", _config_file)

    for sectionname, sub in saved_config.items():
        try:
            section = config[sectionname]
        except KeyError:
            # this section was probably made by another porcupine
            # version or a plugin that isn't loaded
            section = config[sectionname] = _Section()

        for key, value in sub.items():
            try:
                section[key] = value
            except InvalidValue as e:
                # str(e) is like "invalid blah value lulz"
                log.warning("%s, using %r instead", e, section.get(key))

        section._saved_user_values = section._user_values.copy()


def save():
    current_dicty_config = {}
    saved_dicty_config = {}
    for name, section in config.items():
        if section._user_values:
            current_dicty_config[name] = section._user_values
        if section._saved_user_values:
            saved_dicty_config[name] = section._saved_user_values

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
    if current_dicty_config == saved_dicty_config:
        log.info("saving config to '%s'", _config_file)
        with open(_config_file, 'w') as file:
            json.dump(current_dicty_config, file, indent=4)
            file.write('\n')
    else:
        log.info("config hasn't changed, not saving it")
