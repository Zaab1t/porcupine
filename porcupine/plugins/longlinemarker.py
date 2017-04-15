"""Maximum line length marker for Tkinter's text widget."""

import functools
import tkinter as tk
import tkinter.font as tkfont

from porcupine import config, plugins, textwidget, utils

config.add_key('long_line_marker', 'enabled', True)
config.add_key('long_line_marker', 'color', '#ff0000')
config.add_key('long_line_marker', 'column', 79)


class LongLineMarker:

    def __init__(self, textwidget):
        self._frame = tk.Frame(textwidget, width=1)
        self._height = 0   # set_height() will be called
        self._textwidget = textwidget

    def set_color(self, color):
        self._frame['bg'] = color

    def update(self, junk=None):
        if not config.get('long_line_marker', 'enabled'):
            self._frame.place_forget()
            return

        font = tkfont.Font(font=self._textwidget['font'])
        where = font.measure(' ' * config.get('long_line_marker', 'column'))
        self._frame.place(x=where, height=self._height)

    def set_height(self, height):
        self._height = height
        self.update()


def filetab_hook(filetab):
    marker = LongLineMarker(filetab.textwidget)

    def configure_callback(event):
        marker.set_height(event.height)

    connect = functools.partial(config.connect, 'long_line_marker')
    with connect('color', marker.set_color):
        with connect('enabled', marker.update):
            with connect('column', marker.update):
                with config.connect('editing', 'font', marker.update):
                    filetab.textwidget.bind(
                        '<Configure>', configure_callback, add=True)
                    yield


plugins.add_plugin("Long Line Marker", filetab_hook=filetab_hook)


if __name__ == '__main__':
    from porcupine.settings import load as load_settings
    root = tk.Tk()
    load_settings()
    text = tk.Text(root)
    text.pack(fill='both', expand=True)
    marker = LongLineMarker(text)
    text.bind('<Configure>', lambda event: marker.set_height(event.height))
    root.mainloop()
