import logging

log = logging.getLogger(__name__)


def _get_string(obj):
    try:
        return obj.__module__ + '.' + obj.__name__
    except AttributeError:
        return repr(obj)


class CallbackHook:

    def __init__(self):
        self._callbacks = []
        self._currently_hooked = {}     # {args: generator_list, ...}

    def start(self, *args):
        generators = self._currently_hooked[args] = []
        for func in self._callbacks:
            try:
                generator = func(*args)
                next(generator)
            except Exception:
                log.exception("%s doesn't work", _get_string(func))
            else:
                generators.append((_get_string(func), generator))

    def end(self, *args):
        generators = self._currently_hooked.pop(args)
        for string, generator in generators:
            try:
                next(generator)
            except StopIteration:
                # terminated normally
                pass
            except Exception:
                log.exception("%s doesn't work", string)
            else:
                log.error("%s yielded twice", string)

    def hooked(self, *args):
        self.start(*args)
        try:
            yield
        finally:
            self.end(*args)

    def hook(self, function):
        """Add a callback function.

        The function should set things up, yield and then undo
        everything it did.

        You can also use the CallbackHook object as a decorator::

            @some_thingie_hook
            def hookie_callback(some, cool, args):
                ...
        """
        self._callbacks.append(function)

    def unhook(self, function):
        """Undo a :meth:`~hook` call.

        If the hook has been called already it will be ran anyway.
        """
        self._callbacks.remove(function)

    def __call__(self, function):
        self.hook(function)
        return function
