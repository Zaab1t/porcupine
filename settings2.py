import configparser
import glob
import os
import sys
import tkinter as tk
import traceback


class _Config:

    def __init__(self, defaultfile, userfile):
        # The tkinter variables will have 'section:key' names, so they
        # can be easily recognized in trace callbacks.
        self.variables = {}  # {'section:key': tkintervar}

        # The callbacks will be called with the variable name and new
        # value as arguments.
        self._callbacks = []  # {'section:key': callbacklist}

        self._defaultfile = defaultfile
        self._userfile = userfile
        self._default_values = None

    def load(self):
        for string, vartype in vartypedict.items():
            var = vartype(name=string)
            var.trace('w', self._var_changed)
            self.variables[string] = var
            self._callbacks[string] = []

        self._configparser_load(self._defaultfile)
        self._default_values = dict(self)
        self._configparser_load(self._userfile, allow_missing=True)

    def save(self):
        if dict(self) == self._default_values:
            # It's important to check this here because otherwise this
            # may happen:
            #  1. The user opens up two Porcupines. Let's call them A and B.
            #  2. The user changes settings in porcupine A.
            #  3. The user closes Porcupine A and it saves the settings.
            #  4. The user closes Porcupine B and it overwrites the settings
            #     that A saved.
            #  5. The user opens up Porcupine again and the settings are gone.
            # Of course, this doesn't handle the user changing settings
            # in both Porcupines, but I think it's safe to assume that
            # most users don't do that.
            return

        parser = configparser.ConfigParser()
        for string, var in self.variables.items():
            if isinstance(var, tk.StringVar):
                value = var.get()
            elif isinstance(var, tk.BooleanVar):
                value = 'yes' if var.get() else 'no'
            elif isinstance(var, tk.IntVar):
                value = str(var.get())
            else:
                raise TypeError("cannot convert value of %s to configparser "
                                "string" % type(var).__name__)

            sectionname, key = string.split(':')
            try:
                parser[sectionname][key] = value
            except KeyError:
                parser[sectionname] = {key: value}

    def _var_changed(self, varname, *junk):
        try:
            value = self.variables[varname].get()
            for callback in self._callbacks[varname]:
                callback(varname, value)
        except Exception:
            # tkinter suppresses exceptions in trace callbacks :(
            traceback.print_exc()

    def _configparser_load(self, filename, allow_missing=False):
        parser = configparser.ConfigParser()
        parser.read([filename])

        for string, var in self.variables.items():
            sectionname, key = string.split(':')
            try:
                section = parser[sectionname]
                section[key]
            except KeyError as e:
                # the configuration file doesn't have a value for this variable
                if allow_missing:
                    continue
                raise e

            if isinstance(var, tk.BooleanVar):
                var.set(section.getboolean(key))
            elif isinstance(var, tk.IntVar):
                var.set(section.getint(key))
            elif isinstance(var, tk.StringVar):
                var.set(section[key])
            else:
                raise TypeError("unexpected tkinter variable type: "
                                + type(var).__name__)

    # rest of this is convenience stuff
    def connect(self, string, callback):
        self._callbacks[string].append(callback)

    def __setitem__(self, string, value):
        self.variables[string].set(value)

    def __getitem__(self, string, value):
        return self.variables[string].get()

    # allow calling dict() on this
    def keys(self):
        return iter(self.variables)


# we can't create StringVar etc. here because they need a root window
config = _Config()

# color_themes can be a configparser.ConfigParser object, but other
# settings can't be because i want the changes to be applied immediately
# when something is selected in the setting dialog
color_themes = configparser.ConfigParser(default_section='Default')


_here = os.path.dirname(os.path.abspath(__file__))
_user_config_dir = os.path.join(os.path.expanduser('~'), '.porcupine')


def load():
    config._setup({
        'files:encoding': tk.StringVar,
        'files:add_trailing_newline': tk.BooleanVar,
        'editing:font': tk.StringVar,
        'editing:indent': tk.IntVar,    # TODO: allow tabs? (ew)
        'editing:undo': tk.BooleanVar,
        'editing:autocomplete': tk.BooleanVar,
        'editing:color_theme': tk.StringVar,
        'gui:linenumbers': tk.BooleanVar,
        'gui:statusbar': tk.BooleanVar,
        'gui:default_geometry': tk.StringVar,
    })


def _load_config(user_settings=True):
    files = [os.path.join(_here, 'default_settings.ini')]
    if user_settings:
        files.append(os.path.join(_user_config_dir, 'settings.ini'))

    temp_parser = configparser.ConfigParser()
    temp_parser.read(files)

    for string, var in config.items():
        var = config[string]
        sectionname, key = string.split(':')
        section = temp_parser[sectionname]

        if isinstance(var, tk.BooleanVar):
            var.set(section.getboolean(key))
        elif isinstance(var, tk.IntVar):
            var.set(section.getint(key))
        elif isinstance(var, tk.StringVar):
            var.set(section[key])
        else:
            raise TypeError("unexpected tkinter variable type: "
                            + type(var).__name__)


def load():
    for string, vartype in _config_info.items():
        config[string] = vartype()

    os.makedirs(os.path.join(_user_config_dir, 'themes'), exist_ok=True)
    _load_config(user_settings=True)

    color_themes.read(
        [os.path.join(_here, 'default_themes.ini')]
        + glob.glob(os.path.join(_user_config_dir, 'themes', '*.ini'))
    )


def reset_config():
    _load_config(user_settings=False)


_COMMENTS = """\
# This is a Porcupine configuration file. You can edit this manually,
# but any comments or formatting will be lost.
"""


def save():
    parser = configparser.ConfigParser()

    for string, var in config.items():
        if isinstance(var, tk.StringVar):
            value = var.get()
        elif isinstance(var, tk.BooleanVar):
            value = 'yes' if var.get() else 'no'
        elif isinstance(var, tk.IntVar):
            value = str(var.get())
        else:
            raise NotImplementedError(
                "cannot convert value of %s to configparser string"
                % type(var).__name__)

        sectionname, key = string.split(':')
        try:
            parser[sectionname][key] = value
        except KeyError:
            parser[sectionname] = {key: value}

    with open(os.path.join(_user_config_dir, 'settings.ini'), 'w') as f:
        print(_COMMENTS, file=f)
        parser.write(f)
