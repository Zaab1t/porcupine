import abc
import glob
import logging
import os

log = logging.getLogger(__name__)
_plugins = {}     # {name: plugin, ...}


# plugins are code that can be written by user and Porcupine can run
# without, so I think it makes sense to not crash on their errors
def _handle_errors(*args):
    try:
        yield
    except Exception as e:
        # TODO: show the exception info in a message box too?
        log.critical(*args, exc_info=True)


class Plugin:

    def load_session(self, editor):
        """Load and unload everything when the plugin is loaded or unloaded.

        This method should set up the plugin, yield and then undo
        everything it did. It will be called with a porcupine.Editor
        object as the only argument.
        """
        yield

    def load_filetab(self, filetab):
        """Load and unload everything when a new filetab is opened.

        This method should set up a file tab, yield and then undo
        everything it did. It will be called with a
        porcupine.filetabs.FileTab object as the only argument.
        """
        yield

    def make_setting_widget(self, labelframe):
        """This is called when the setting dialog is opened for the first time.

        This method should create other tkinter widgets for changing the
        settings into the given tkinter LabelFrame widget. The
        labelframe is displayed in the setting dialog only if this
        method returns True.
        """
        return False


def add_plugin(name, plugin_class=None):
    """Register a plugin class.

    You can create a new Porcupine plugin like this:

     1. Create a Python file that imports porcupine and defines a class
        that inherits from porcupine.Plugin and is decorated with
        porcupine.add_plugin.
     2. Move the plugin file to the plugins/ directory in your Porcupine
        setting directory.
     3. Reload plugins in Porcupine.
    """
    if plugin_class is None:
        # used as a decorator
        return functools.partial(add_plugin, name)


# rest of this file contains things that are not exposed in __init__.py

def _relative_glob(dirpath, pattern):
    return glob.glob(os.path.join(glob.escape(dirpath), pattern))


def load_plugins():
    if _plugins:
        raise RuntimeError("cannot load plugins twice")

    for plugindir in [os.path.expanduser('~/.porcupine/plugins'),
                      os.path.join(os.path.dirname(__file__), 'plugins')]:
        for file in os.listdir(path):
            if not file.endswith('.py'):
                continue
            path = os.path.join(plugindir, file)

            before_

            try:
                runpy.run_path(file)
            except Exception as e:
                log.exception("problem with loading plugin file '%s'", file)
            else:
                log.debug("loaded plugins from '%s'", file)

    log.info("loaded %d plugins", len(_plugins))
