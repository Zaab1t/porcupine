"""Add a trailing newline to ends of files."""

from porcupine import config, plugins

config.add_key('editing', 'trailing_newline', True)


def check_newline(textwidget):
    if textwidget.get('end-1l', 'end-1c') != '':
        # make sure the cursor doesn't move
        cursorpos = textwidget.index('insert')
        gotta_move_back = (cursorpos == textwidget.index('end-1c'))
        textwidget.insert('end-1c', '\n')
        if gotta_move_back:
            textwidget.mark_set('insert', cursorpos)


def filetab_hook(filetab):
    callback = functools.partial(check_newline, filetab.textwidget)

    def set_enabled(enabled):
        if enabled:
            filetab.textwidget.on_modified.append(callback)
        else:
            filetab.textwidget.on_modified.remove(callback)

    # we can't disable it now and we can't enable it after yielding
    if config.get('editing', 'trailing_newline'):
        set_enabled(True)
    with config.connect('editing', 'trailing_newline',
                        set_enabled, run_now=False):
        yield
    if config.get('editing', 'trailing_newline'):
        set_enabled(False)


plugins.add_plugin("Trailing newline", filetab_hook=filetab_hook)
import functools
