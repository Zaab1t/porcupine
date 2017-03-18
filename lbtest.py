import functools
import tkinter as tk


# tkinter.OptionMenu doesn't look that nice on either Windows or any of
# my Linux desktop environments and it's also based on "obsolite"
# tkinter.Menubutton (see help('tkinter.Menubutton')), so this should be
# better
class DropdownMenu(tk.Frame):

    def __init__(self, parent, variable, choices, **kwargs):
        super().__init__(parent, **kwargs)
        self._var = variable
        self._showing = False

        self._menu = tk.Menu(tearoff=False)
        for choice in choices:
            self._add_menu_item(choice)

        self._text = tk.Label(self, textvariable=variable,
                              pady=0, anchor='w')
        self._text.pack(side='left', fill='both', expand=True)

        # this makes the text label look like an entry
        entry = tk.Entry()
        for option in ['foreground', 'background', 'relief']:
            self._text[option] = entry[option]
        entry.destroy()

        # chr(9660) is Unicode arrow down
        self._button = tk.Label(self, text=chr(9660), relief='raised')
        self._button.pack(side='right', fill='y')

        for label in [self._text, self._button]:
            label['padx'] = label['pady'] = 2
            label.bind('<Button-1>', self._toggle)

    def _add_menu_item(self, text):
        def callback():
            self._var.set(text)
            self._hide()
        self._menu.add_command(label=text, command=callback)

    def _show(self):
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._menu.post(x, y)
        self._button['relief'] = 'sunken'
        self._showing = True

    def _hide(self):
        self._menu.unpost()
        self._button['relief'] = 'raised'
        self._showing = False

    def _toggle(self, event=None):
        if self._showing:
            self._hide()
        else:
            self._show()


root = tk.Tk()
var = tk.StringVar()
var.set('a')
var.trace('w', lambda *junk: print("value changed to", var.get()))
m = DropdownMenu(root, var, ['a', 'b', 'c'])
m.pack(fill='x')
root.geometry('100x100')
root.mainloop()
