import operator
import tkinter as tk
from tkinter import colorchooser

# TODO: use the plugins here?
from porcupine import config
from porcupine.textwidget import ThemedText


_SAMPLE_SCRIPT = """\
print("Hello World")
word = input("Enter something: ")
if word == "hi":
    print("Howdy Hi!")
else:
    print("You didn't enter hi :(")
"""


def _more_brightness(rgb, how_much):
    result = []
    for value in rgb:
        value += how_much
        if value < 0:
            result.append(0)
        elif value > 0xff:
            result.append(0xff)
        else:
            result.append(value)
    return '#%02x%02x%02x' % tuple(result)


class ColorButton(tk.Button):

    def __init__(self, parent, color, **kwargs):
        super().__init__(parent, command=self._on_click, **kwargs)
        self.on_color_changed = []
        self.color = color

    # this is public because it can be used as a handy callback
    def set_color(self, color):
        # winfo_rgb returns 16-bit integers but usually RGB colors are
        # represented as 8-bit integers
        r, g, b = (value >> 8 for value in self.winfo_rgb(color))
        hexresult = '#%02x%02x%02x' % (r, g, b)
        self['bg'] = self['text'] = hexresult

        if (r + g + b) / 3 < 0xff / 2:
            # it's dark
            self['fg'] = self['activeforeground'] = 'white'
            self['activebackground'] = _more_brightness([r, g, b], 50)
        else:
            self['fg'] = self['activeforeground'] = 'black'
            self['activebackground'] = _more_brightness([r, g, b], -50)

        for callback in self.on_color_changed:
            callback(hexresult)

    def _get_color(self):
        return self['bg']

    color = property(_get_color, set_color)

    def _on_click(self):
        junky_rgb, hexcolor = colorchooser.askcolor(self.color)
        if hexcolor is not None:
            # not cancelled
            self.color = hexcolor


class ThemeChooser(tk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._theme_name = None

        self._listbox = tk.Listbox(self)
        self._listbox.pack(side='left', fill='both', expand=True)
        self._listbox.bind('<<ListboxSelect>>', self._on_select)

        self._scrollbar = tk.Scrollbar(self)
        self._scrollbar.pack(side='left', fill='y')
        self._listbox['yscrollcommand'] = self._scrollbar.set
        self._scrollbar['command'] = self._listbox.yview

        for name in sorted(config.color_themes):
            self._listbox.insert('end', name)
            if name == config.get('general', 'color_theme'):
                self._listbox.select_set('end')

    def set_theme_name(self, name):
        if self._theme_name == name:
            return
        print("u selected", name)

    def _on_select(self, event):
        self.set_theme_name(event.widget.selection_get())


if __name__ == '__main__':
    root = tk.Tk()
    config.load()

    chooser = ThemeChooser(root)
    chooser.pack(fill='both', expand=True)

    root.mainloop()
