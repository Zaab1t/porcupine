"""Convert tabs to spaces when needed.

This is done by handling all Tab events and forwarding them to
textwidget.MainText.indent and textwidget.MainText.dedent. This plugin
must be loaded after all other plugins that bind tab or shift+tab.
"""

import porcupine
from porcupine import tabs, utils


def on_tab(event, shift_pressed):
    if not event.widget.tag_ranges('sel'):
        # nothing selected
        if shift_pressed:
            event.widget.dedent('insert')
        else:
            event.widget.indent('insert')

    # don't insert a tab when it's not supposed to be inserted, or if
    # shift is pressed down, don't move focus out of the widget
    return 'break'


def on_new_tab(event):
    tab = event.widget.tabs[-1]
    if isinstance(tab, tabs.FileTab):
        utils.bind_tab_key(tab.textwidget, on_tab, add=True)


def setup():
    porcupine.get_tab_manager().bind('<<NewTab>>', on_new_tab, add=True)
