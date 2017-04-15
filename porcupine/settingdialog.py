"""A dialog for changing the settings."""

# This uses ttk widgets instead of tk widgets because it needs
# ttk.Combobox anyway and mixing the widgets looks inconsistent.

import re
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont

from porcupine import config, utils


try:
    # There's no ttk.Spinbox for some reason. Maybe this will be fixed
    # later?
    _TtkSpinbox = ttk.Spinbox
except AttributeError:
    # At least not yet, but implementing this is easy to do by reading
    # the code of ttk.Combobox.
    class _TtkSpinbox(ttk.Entry):
        def __init__(self, master=None, *, from_=None, **kwargs):
            if from_ is not None:
                kwargs['from'] = from_  # this actually works
            super().__init__(master, 'ttk::spinbox', **kwargs)


class _ConfigMixin:

    def __init__(self, parent, section, key, **kwargs):
        super().__init__(parent, **kwargs)
        self._section = section
        self._key = key
        self._triangle = ttk.Label(parent)
        config.connect(self._section, self._key, self.from_config)

    # i didn't feel like using an abc
    def from_config(self, value):
        raise NotImplementedError("from_config() must be overrided")

    def to_config(self, value):
        config.set(self._section, self._key, value)

    def show_triangle(self):
        self._triangle['image'] = utils.get_image('triangle.gif')

    def hide_triangle(self):
        self._triangle['image'] = ''

    def destroy(self):
        config.disconnect(self._section, self._key, self.from_config)
        super().destroy()


class Checkbutton(_ConfigMixin, ttk.Checkbutton):

    def __init__(self, *args, **kwargs):
        self._var = tk.BooleanVar()
        super().__init__(*args, variable=self._var, **kwargs)
        self._var.trace('w', self.to_config)

    def to_config(self, *junk):
        super().to_config(self._var.get())

    def from_config(self, value):
        self._var.set(value)


class Entry(_ConfigMixin, ttk.Entry):

    def __init__(self, *args, **kwargs):
        self._var = tk.StringVar(value=config[key])
        super().__init__(*args, textvariable=self._var, **kwargs)
        self._var.trace('w', self.to_config)

    def to_config(self, *junk):
        try:
            super().to_config(self._var.get())
            self.hide_triangle()
        except config.InvalidValue:
            self.show_triangle()

    def from_config(self, value):
        self._var.set(value)


class Spinbox(_ConfigMixin, _TtkSpinbox):

    def __init__(self, *args, **kwargs):
        self._var = tk.StringVar()
        super().__init__(self, textvariable=self._var, **kwargs)
        var.trace('w', self.to_config)

    def to_config(self, *junk):
        try:
            super().to_config(int(self._var.get()))
            self.hide_triangle()
        except ValueError:
            self.show_triangle()

    def from_config(self, value):
        self._var.set(str(value))


class FontSelector(_ConfigMixin, ttk.Frame):

    def __init__(self, *args, **kwargs):
        self._familyvar = tk.StringVar()
        self._sizevar = tk.StringVar()
        super().__init__(*args, **kwargs)
        self._familyvar.trace('w', self.to_config)
        self._sizevar.trace('w', self.to_config)

        family_combobox = ttk.Combobox(
            self, textvariable=self._familyvar, values=self._list_families())
        family_combobox['width'] -= 4  # not much bigger than other widgets
        family_combobox.pack(side='left')
        size_spinbox = _TtkSpinbox(self, textvariable=self._sizevar,
                                  from_=1, to=999, width=4)
        size_spinbox.pack(side='left')

    def to_config(self, *junk):
        family = self._familyvar.get()
        try:
            size = int(self._sizevar.get())
            super().to_config([family, size])
            self.hide_triangle()
        except ValueError:
            self.show_triangle()

    def from_config(self, value):
        family, size = value
        self._familyvar.set(family)
        self._sizevar.set(str(size))

    def _list_families(self):
        result = set()
        for family in tkfont.families():
            # windows has weird fonts that start with @
            if not family.startswith('@'):
                result.add(family)
        return sorted(result, key=str.casefold)


class _LabelFrame(ttk.LabelFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.row = 0
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(2, minsize=20)

    def add_widget(self, widget, label=None, triangle=None):
        if label is None:
            widget.grid(row=self.row, column=0, columnspan=2, sticky='w')
        else:
            if isinstance(label, str):
                label = ttk.Label(self, text=label)
            label.grid(row=self.row, column=0, sticky='w')
            widget.grid(row=self.row, column=1, sticky='e')
        if hasattr(widget, '_triangle'):
            widget._triangle.grid(row=self.row, column=2)
        self.row += 1


class _SettingEditor(ttk.Frame):

    def __init__(self, *args, ok_callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._ok_callback = ok_callback
        self._labelframes = {}
        self._create_buttons()

    def get_labelframe(self, text):
        if text not in self._labelframes:
            self._labelframes[text] = _LabelFrame(self, text=text)
        return self._labelframes[text]

    def _create_buttons(self):
        frame = ttk.Frame(self)
        frame.pack(side='bottom', fill='x')

        okbutton = ttk.Button(frame, width=6, text="OK")
        okbutton.pack(side='right')
        if self._ok_callback is not None:
            okbutton['command'] = self._ok_callback
        resetbutton = ttk.Button(
            frame, width=6, text="Reset", command=self.reset)
        resetbutton.pack(side='right')

        ttk.Separator(self).pack(side='bottom', fill='x')

    def reset(self):
        confirmed = messagebox.askyesno(
            "Reset settings", "Do you want to reset all settings to defaults?",
            parent=self)
        if confirmed:
            config.reset()
            messagebox.showinfo(
                "Reset settings", "All settings were reset to defaults.",
                parent=self)


class __OldJunk:

    def _create_filesection(self):
        section = _LabelFrame(self, text="Files")
        section.add_entry(
            'files:encoding', label="Encoding of opened and saved files:")
        section.add_checkbox(
            'files:add_trailing_newline',
            text="Make sure that files end with an empty line when saving")
        return section

    def _add_long_line_marker(self, section):
        checkbox = section.add_checkbox(
            'editing:longlinemarker',
            text="Display a long line marker at this column:")
        section.row -= 1    # overwrite same row again
        spinbox = section.add_spinbox('editing:maxlinelen', from_=1, to=200,
                                      label=checkbox)

        @config.connect('editing:longlinemarker')
        def on_check(value):
            if value:
                spinbox['state'] = 'normal'
            else:
                spinbox['state'] = 'disabled'

    def _create_editingsection(self):
        section = _LabelFrame(self, text="Editing")
        section.add_font_selector(
            'editing:font', label="Font family and size:")
        section.add_spinbox(
            'editing:indent', from_=1, to=100, label="Indent width:")
        section.add_checkbox(
            'editing:undo', text="Enable undo and redo")
        section.add_checkbox(
            'editing:autocomplete', text="Autocomplete with tab")
        self._add_long_line_marker(section)
        return section

    def _create_guisection(self):
        section = _LabelFrame(self, text="The GUI")
        section.add_checkbox(
            'gui:linenumbers', text="Display line numbers")
        section.add_checkbox(
            'gui:statusbar', text="Display a statusbar at bottom")
        section.add_entry(
            'gui:default_geometry',
            label="Default window size as a Tkinter geometry (e.g. 650x500):")
        return section


if __name__ == '__main__':
    import porcupine.plugins.linenumbers  # noqa

    root = tk.Tk()
    root.title("Porcupine Settings")
    config.load()

    editor = _SettingEditor(root, ok_callback=root.destroy)
    editor.pack(fill='both', expand=True)

    checkbox = Checkbutton(
        editor.get_labelframe("Line numbers"), 'editing',
        'linenumbers', text="Display line numbers")
    checkbox.pack()

    try:
        # the dialog is usable only if we get here, so we don't need to
        # wrap the whole thing in try/finally
        root.mainloop()
    finally:
        config.save()
