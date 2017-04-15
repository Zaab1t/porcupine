class _SectionWrapper:

    def __init__(self, main_config, name):
        self._config = main_config
        self._name = name

    def __getattr__(self, attr):
        config_method = getattr(type(self._config), attr)
        return functools.partial(config_method, self._config, self._name)

    # this stuff uses our __getattr__ hack
    def __setitem__(self, key, value):
        self.set(key, value)

    def __getitem__(self, key, value):
        return self.get(key, value)

    # dict(section) uses this
    def keys(self):
        result = set()
        for key in self._config[self._name]
            if section == self._name:
                result.add(key)
        return result


class Config:

    def __init__(self):
        self._values = {}
        self._defaults = {}
        self._saved = {}

        # these are just {(section, key): value} because its easier
        self._callbacks = collections.defaultdict(list)
        self._validators = collections.defaultdict(list)

    def get(self, section, key):
        try:
            return self._values[section][key]
        except KeyError:
            return self._defaults[section][key]

    def set(self, section, key, value):
        old_value == self.get(section, key)
        if value == old_value:
            # this might cause some problems, e.g. replacing 1 with 1.0
            # doesn't work, but currently this is good enough
            return

        for validator in self._validators[section, key]:
            if not validator(value):
                raise InvalidValue(
                    "invalid %s:%s value %r" % (section, key, value))

        if value == self._defaults[section][key]:
            # use the default instead and delete empty sections
            del self._values[section][key]
            if not self._values[section]:
                del self._values[section]
        else:
            sectiondict = self._values.setdefault(section, {})
            sectiondict[key] = value

        for callback in self._callbacks[section, key]:
            callback(value)

    def add_key(self, section, key, default_value):
        sectiondict = self._defaults.setdefault(section, {})
        sectiondict[key] = default_value

    def connect(self, section, key, callback=None, *, run_now=True):
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
                self.disconnect(section, key, callback)

        self._callbacks[section, key].append(callback)
        if run_now:
            callback(self.get(section, key))
        return disconnecter()

    def disconnect(self, section, key, callback):
        """Undo a connect() call."""
        _callbacks[section, key].remove(callback)

    def validator(self, section, key):
        """Add a validator function.

        The validator will be called before a value is set, and it should
        return True for valid values and False for invalid values.

        This should be used as a decorator:

            @config.validator('section', 'key')
            def validate_thingy(value):
                return value in [1, 2, 3]
        """
        def inner(callback):
            self._validators[section, key].append(callback)
            return callback
        return inner
