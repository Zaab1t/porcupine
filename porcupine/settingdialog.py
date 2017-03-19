"""A dialog for changing the settings."""

import base64
import codecs
import os
import pkgutil
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont

from porcupine.settings import config

_PADDING = {'padx': 5, 'pady': 2}


try:
    # There's no ttk.Spinbox for some reason. Maybe this will be fixed
    # later?
    TtkSpinbox = ttk.Spinbox
except AttributeError:
    # At least not yet, but implementing this is easy to do by reading
    # the code of ttk.Combobox.
    class TtkSpinbox(ttk.Entry):
        def __init__(self, master=None, *, from_=None, **kwargs):
            if from_ is not None:
                kwargs['from'] = from_  # this actually works
            super().__init__(master, 'ttk::spinbox', **kwargs)


def _create_checkbox(parent, *, text='', **kwargs):
    """Create a widget like like tk.Checkbutton.

    Unlike tk.Checkbutton, this doesn't screw up with dark GTK+ themes.
    tk.Checkbutton displays a white checkmark on a white background on
    my dark GTK+ 2 theme.
    """
    # I'm aware of ttk.Checkbutton, but ttk widgets display a light-gray
    # background on my dark GTK+ theme.

    # we can't use the checkbutton's text because the colors of the text
    # also change when the checkmark colors are changed :(
    frame = tk.Frame(parent)
    checkbox = tk.Checkbutton(frame, foreground='black',
                              selectcolor='white', **kwargs)
    checkbox.pack(side='left')
    label = tk.Label(frame, text=text)
    label.pack(side='right', fill='both', expand=True)

    # now we need to make the label behave like a part of the checkbox
    def redirect_events(event_string):
        def callback(event):
            checkbox.event_generate(event_string)
        label.bind(event_string, callback)

    redirect_events('<Button-1>')
    redirect_events('<Enter>')
    redirect_events('<Leave>')

    # the checkbox isn't easy to access, but it doesn't matter for this
    return frame


def _list_families():
    result = {'TkFixedFont'}   # a set to delete duplicates
    for family in tkfont.families():
        # There are some weird fonts starting with @ on Windows for some
        # reason.
        if not family.startswith('@'):
            result.add(family)
    return sorted(result, key=str.casefold)


class _WarningTriangle(tk.Label):

    _image_cache = {}

    def __init__(self, *args, **kwargs):
        if not self._image_cache:
            data = pkgutil.get_data('porcupine', 'images/triangle.png')
            triangle = tk.PhotoImage(data=base64.b64encode(data))
            empty = tk.PhotoImage(width=triangle.width(),
                                  height=triangle.height())
            self._image_cache['triangle'] = triangle
            self._image_cache['empty'] = empty

        super().__init__(*args, **kwargs)
        self.hide()

    def show(self):
        self['image'] = self._image_cache['triangle']

    def hide(self):
        self['image'] = self._image_cache['empty']


class _Section(tk.LabelFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._row = 0
        self.grid_columnconfigure(0, weight=1)

    def add_widget(self, widget, text=None, triangle=None):
        if text is None:
            widget.grid(row=self._row, column=0, columnspan=2,
                        sticky='w', **_PADDING)
        else:
            label = tk.Label(self, text=text)
            label.grid(row=self._row, column=0, sticky='w', **_PADDING)
            widget.grid(row=self._row, column=1, sticky='e', **_PADDING)
        if triangle is not None:
            triangle.grid(row=self._row, column=2)
        self._row += 1

    def add_checkbox(self, key, **kwargs):
        checkbox = _create_checkbox(
            self, variable=config.variables[key], **kwargs)
        self.add_widget(checkbox)

    def add_entry(self, key, *, text, **kwargs):
        var = tk.StringVar()
        var.set(config[key])
        entry = tk.Entry(self, textvariable=var, **kwargs)
        triangle = _WarningTriangle(self)

        def to_config(*junk):
            value = var.get()
            if config.validate(key, value):
                triangle.hide()
                config[key] = value
            else:
                triangle.show()

        def from_config(key, value):
            var.set(value)

        var.trace('w', to_config)
        config.connect(key, from_config)
        self.add_widget(entry, text, triangle)

    def add_spinbox(self, key, *, text, **kwargs):
        var = tk.StringVar()
        var.set(str(config[key]))
        spinbox = tk.Spinbox(self, textvariable=var, **kwargs)
        triangle = _WarningTriangle(self)

        def to_config(*junk):
            try:
                value = int(var.get())
                if not config.validate(key, value):
                    raise ValueError
            except ValueError:
                triangle.show()
                return
            triangle.hide()
            config[key] = value

        def from_config(key, value):
            var.set(str(value))

        var.trace('w', to_config)
        config.connect(key, from_config)
        self.add_widget(spinbox, text, triangle)

    def add_font_selector(self, key, *, text, **kwargs):
        familyvar = tk.StringVar()
        sizevar = tk.StringVar()

        frame = tk.Frame(self)
        family_combobox = ttk.Combobox(
            frame, textvariable=familyvar, values=_list_families())
        family_combobox['width'] -= 4  # about same size as other widgets
        family_combobox.pack(side='left')
        size_spinbox = TtkSpinbox(
            frame, textvariable=sizevar, from_=1, to=100, width=4)
        size_spinbox.pack(side='left')

        triangle = _WarningTriangle(self)

        # not all values that the user types are valid, so we need to
        # cache the previous correct family and size
        cache = []   # ['family', size]

        def from_config(key, value):
            # the fonts are stored as "{family} size" strings because
            # tkinter widgets can use strings like that
            if value.lower() == 'tkfixedfont':
                # Special case: tkinter's default font. The cache needs
                # to be set before setting the variables because
                # to_config() needs the cache.
                cache[:] = ['TkFixedFont', None]
                familyvar.set('TkFixedFont')
                sizevar.set('N/A')
            else:
                print(repr(value))
                match = re.search(r'^\{(.+)\} (\d+)$', value)
                cache[:] = [match.group(1), int(match.group(2))]
                familyvar.set(match.group(1))
                sizevar.set(match.group(2))
 
        def to_config(*junk):
            family = familyvar.get()
            ok = True

            if family.lower() == 'tkfixedfont':
                # special family
                cache[:] = ['TkFixedFont', None]
                sizevar.set('N/A')

            elif family.casefold() in map(str.casefold, _list_families()):
                # family is ok, how about size?
                cache[0] = family
                try:
                    size = int(sizevar.get())
                    if size <= 0:
                        raise ValueError
                    cache[1] = size
                except ValueError:   # int() failed
                    ok = False

            else:
                # family is not ok
                ok = False

            if ok:
                triangle.hide()
                if cache == ['TkFixedFont', None]:
                    config[key] = 'TkFixedFont'
                else:
                    config[key] = '{%s} %d' % tuple(cache)
            else:
                triangle.show()

        familyvar.trace('w', to_config)
        sizevar.trace('w', to_config)
        config.connect(key, from_config)
        from_config(key, config[key])
        self.add_widget(frame, text, triangle)


class SettingDialog(tk.Toplevel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.on_close = self.destroy
        self.protocol('WM_DELETE_WINDOW', self._close_me)

        filesection = self._create_filesection()
        editingsection = self._create_editingsection()
        guisection = self._create_guisection()
        separator = tk.Frame(self, height=3, border=1, relief='sunken')
        buttonframe = self._create_buttons()

        for widget in [filesection, editingsection, guisection,
                       separator, buttonframe]:
            widget.pack(fill='x', **_PADDING)

    def _close_me(self):
        """Call self.on_close().

        This is needed because it's possible to set on_close to another
        callback function after creating the SettingDialog.
        """
        self.on_close()

    def _create_filesection(self):
        section = _Section(self, text="Files")
        section.add_entry(
            'files:encoding', text="Encoding of opened and saved files:")
        section.add_checkbox(
            'files:add_trailing_newline',
            text="Make sure that files end with an empty line when saving")
        return section

    def _create_editingsection(self):
        section = _Section(self, text="Editing")
        section.add_font_selector(
            'editing:font', text="Font family and size:")
        section.add_spinbox(
            'editing:indent', from_=1, to=100, text="Indent width:")
        section.add_checkbox(
            'editing:undo', text="Enable undo and redo")
        section.add_checkbox(
            'editing:autocomplete', text="Autocomplete with tab")
        return section

    def _create_guisection(self):
        section = _Section(self, text="The GUI")
        section.add_checkbox(
            'gui:linenumbers', text="Display line numbers")
        section.add_checkbox(
            'gui:statusbar', text="Display a statusbar at bottom")
        section.add_entry(
            'gui:default_geometry',
            text=("Default window size as a Tkinter geometry " +
                  "(e.g. 650x500):"))
        return section

    def _create_buttons(self):
        frame = tk.Frame(self)
        ok = tk.Button(frame, width=6, text="OK", command=self._close_me)
        ok.pack(side='right', **_PADDING)
        reset = tk.Button(frame, width=6, text="Reset", command=self.reset)
        reset.pack(side='right', **_PADDING)
        return frame

    def reset(self):
        confirmed = messagebox.askyesno(
            self.title(), "Do you want to reset all settings to defaults?",
            parent=self)
        if confirmed:
            config.reset()
            messagebox.showinfo(
                self.title(), "All settings were reset to defaults.",
                parent=self)


if __name__ == '__main__':
    import porcupine.settings

    root = tk.Tk()
    root.withdraw()

    porcupine.settings.load()
    dialog = SettingDialog()
    dialog.title("Porcupine Settings")
    dialog.on_close = root.destroy

    # the dialog is usable only if we get here, so we don't need to wrap
    # the whole thing in try/finally
    try:
        root.mainloop()
    finally:
        porcupine.settings.save()