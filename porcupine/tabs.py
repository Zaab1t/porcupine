r"""Tabs as in browser tabs, not \t characters."""

import functools
import hashlib
import itertools
import logging
import os
import tkinter
from tkinter import ttk, messagebox
import traceback

import porcupine
from porcupine import _dialogs, filetypes, settings, textwidget, utils

log = logging.getLogger(__name__)
_flatten = itertools.chain.from_iterable


class TabManager(ttk.Notebook):
    """A simple but awesome tab widget.

    This widget is a lot like ``ttk.Notebook``, but this class also
    implements split views and only :class:`Tab` can be added to this.

    .. virtualevent:: NewTab

        This runs when a new tab has been added to the tab manager with
        :meth:`add_tab`. Use :func:`~porcupine.utils.bind_with_data` and
        ``event.data_widget`` to access the tab that was added.

        Bind to the ``<Destroy>`` event of the tab if you want to clean
        up something when the tab is closed.

    .. virtualevent:: CurrentTabChanged

        This runs when the user selects another tab or Porcupine does it
        for some reason. Use ``event.widget.current_tab`` to get or set
        the currently selected tab.

        .. seealso:: :attr:`~current_tab`

    .. attribute:: tabs

        List of Tab objects in the tab manager.

        Don't modify this list yourself, use methods like
        :meth:`~move_left`, :meth:`~move_right`, :meth:`~add_tab` or
        :meth:`~close_tab` instead.

    .. attribute:: current_tab

        The tab that the user has currently selected.

        This is None when there are no tabs. You can set this to select
        a tab, like this::

            tabmanager.current_tab = some_tab

    .. attribute:: current_index

        .. warning:: Don't use this attribute. I may remove it later.

        The index of :attr:`~current_tab` in :attr:`~tabs`.

        Setting this raises :exc:`IndexError` if the index is too big or
        too small. Negative indexes are not supported.

    .. method:: add(child, **kw)
    .. method:: enable_traversal()
    .. method:: hide(tab_id)
    .. method:: index(tab_id)
    .. method:: insert(pos, child, **kw)
    .. method:: select(tab_id=None)
    .. method:: tab(tab_id, option=None, **kw)
    .. method:: tabs()

        Don't use these methods. Currently ``TabManager`` inherits from
        ``ttk.Notebook``, but that may be changed later. These methods
        come from ``ttk.Notebook``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # These can be bound in a parent widget. This doesn't use
        # enable_traversal() because we want more bindings than it
        # creates.
        # TODO: document these?
        partial = functools.partial     # pep-8 line length
        self.bindings = [
            ('<Control-Prior>', partial(self._on_page_updown, False, -1)),
            ('<Control-Next>', partial(self._on_page_updown, False, +1)),
            ('<Control-Shift-Prior>', partial(self._on_page_updown, True, -1)),
            ('<Control-Shift-Next>', partial(self._on_page_updown, True, +1)),
        ]
        for number in range(1, 10):
            callback = functools.partial(self._on_alt_n, number)
            self.bindings.append(('<Alt-Key-%d>' % number, callback))

        self.bind('<<NotebookTabChanged>>', self._on_tab_changed, add=True)

    def _on_page_updown(self, shifted, diff, event):
        assert diff in {1, -1}, repr(diff)

        if shifted:     # move the tab
            # make sure that i1 < i2
            if diff == +1:
                i1 = self.index(self.current_tab)
                i2 = i1 + 1
            else:
                i2 = self.index(self.current_tab)
                i1 = i2 - 1

            if i1 >= 0 and i2 < self.index('end'):
                # it's important to move the second tab back instead of moving
                # the other tab forward because insert(number_of_tabs, tab)
                # doesn't work for some reason
                tab = self.tabs[i2]
                options = self.tab(i2)
                self.forget(i2)
                self.insert(i1, tab, **options)
                if diff == -1:      # the moved tab was selected
                    self.current_tab = tab

        else:
            # select another tab
            index = self.index(self.select())
            try:
                self.select(index + diff)
            except tkinter.TclError:  # should be "Slave index n out of bounds"
                pass

        return 'break'

    def _on_alt_n(self, n, event):
        try:
            self.current_tab = self.tabs[n - 1]
            return 'break'
        except IndexError:
            return None

    def _on_tab_changed(self, event):
        self.nametowidget(self.select()).on_focus()
        self.event_generate('<<CurrentTabChanged>>')

    # careful not to do self.tabs() everywhere
    @property
    def tabs(self):
        return list(map(self.nametowidget, super().tabs()))

    @property
    def current_tab(self):
        if self.tabs:
            return self.nametowidget(self.select())
        return None

    @current_tab.setter
    def current_tab(self, tab):
        self.select(tab)

    def add_tab(self, tab, make_current=True):
        """Append a :class:`.Tab` to this tab manager.

        If ``tab.equivalent(existing_tab)`` returns True for any
        ``existing_tab`` that is already in the tab manager, then that
        existing tab is returned. Otherwise *tab* is added to the tab
        manager and returned.

        If *make_current* is True, then :attr:`current_tab` is set to
        the tab that is returned.

        .. seealso::
            The :meth:`.Tab.equivalent` and :meth:`~close_tab` methods.
        """
        assert tab not in self.tabs, "cannot add the same tab twice"
        for existing_tab in self.tabs:
            if tab.equivalent(existing_tab):
                if make_current:
                    self.current_tab = existing_tab
                return existing_tab

        self.add(tab, text=tab.title, image='img_closebutton',
                 compound='right')
        if make_current:
            self.current_tab = tab

        # the update() is needed in some cases because virtual events
        # don't run if the widget isn't visible yet
        self.update()
        self.event_generate('<<NewTab>>', data=tab)
        return tab

    def close_tab(self, tab):
        """Destroy a tab without calling :meth:`~Tab.can_be_closed`.

        The closed tab cannot be added back to the tab manager later.

        .. seealso:: The :meth:`.Tab.can_be_closed` method.
        """
        self.forget(tab)
        tab.destroy()


class Tab(ttk.Frame):
    r"""Base class for widgets that can be added to TabManager.

    You can easily create custom kinds of tabs by inheriting from this
    class. Here's a very minimal but complete example plugin::

        import tkinter as tk
        import porcupine
        from porcupine import tabs

        class HelloTab(tabs.Tab):
            def __init__(self, manager):
                super().__init__(manager)
                self.title = "Hello"
                tk.Label(self, text="Hello World!").pack()

        def new_hello_tab():
            manager = porcupine.get_tab_manager()
            manager.add_tab(HelloTab(manager))

        def setup():
            porcupine.add_action(new_hello_tab, 'Hello/New Hello Tab')

    Note that you need to use the pack geometry manager when creating
    custom tabs. If you want to use grid or place you can create a frame
    inside the tab, pack it with ``fill='both', expand=True`` and do
    whatever you want inside it.

    .. virtualevent:: StatusChanged

        This event is generated when :attr:`status` is set to a new
        value. Use ``event.widget.status`` to access the current status.

    .. attribute:: title

        This is the title of the tab, next to the red close button. You
        can set and get this attribute easily.

    .. attribute:: status

        A human-readable string for showing in e.g. a status bar.

        The status message can also contain multiple tab-separated
        things, e.g. ``"File 'thing.py'\tLine 12, column 34"``.

        This is ``''`` by default, but that can be changed like
        ``tab.status = something_new``.

        If you're writing something like a status bar, make sure to
        handle ``\t`` characters and bind :virtevt:`~StatusChanged`.

    .. attribute:: master

        Tkinter sets this to the parent widget. Use this attribute to
        access the :class:`TabManager` of a tab.

    .. attribute:: top_frame
    .. attribute:: bottom_frame
    .. attribute:: left_frame
    .. attribute:: right_frame

        These are ``ttk.Frame`` widgets that are packed to each side of
        the frame. Plugins add different kinds of things to these, for
        example, :source:`the statusbar <porcupine/plugins/statusbar.py>`
        is a widget in ``bottom_frame``.

        These frames should contain no widgets when Porcupine is running
        without plugins. Use pack when adding things here.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self._status = ''
        self._title = ''

        # top and bottom frames must be packed first because this way
        # they extend past other frames in the corners
        self.top_frame = ttk.Frame(self)
        self.bottom_frame = ttk.Frame(self)
        self.left_frame = ttk.Frame(self)
        self.right_frame = ttk.Frame(self)
        self.top_frame.pack(side='top', fill='x')
        self.bottom_frame.pack(side='bottom', fill='x')
        self.left_frame.pack(side='left', fill='y')
        self.right_frame.pack(side='right', fill='y')

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, new_status):
        self._status = new_status
        self.event_generate('<<StatusChanged>>')

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, text):
        self._title = text
        if self in self.master.tabs:    # lol
            self.master.tab(self, text=text)    # lel

    def can_be_closed(self):
        """
        This is usually called before the tab is closed. The tab
        shouldn't be closed if this returns False.

        By default, this always returns True, but you can override this
        in a subclass to do something more interesting. See
        :meth:`.FileTab.can_be_closed` for an example.
        """
        return True

    def on_focus(self):
        """This is called when the tab is selected.

        This does nothing by default. You can override this in a
        subclass and make this focus the tab's main widget if needed.
        """

    def equivalent(self, other):
        """This is explained in :meth:`.TabManager.add_tab`.

        This always returns False by default, but you can override it in
        a subclass. For example::

            class MyCoolTab(tabs.Tab):
                ...

                def equivalent(self, other):
                    if isinstance(other, MyCoolTab):
                        # other can be used instead of this tab if its
                        # thingy is same as this tab's thingy
                        return (self.thingy == other.thingy)
                    else:
                        # MyCoolTabs are never equivalent to other kinds
                        # of tabs
                        return False
        """
        return False

    def get_state(self):
        """Override this method to support opening a similar tab after \
restarting Porcupine.

        When Porcupine is closed,
        :source:`the restart plugin <porcupine/plugins/restart.py>`
        calls :meth:`get_state` methods of all tabs, and after starting
        Porcupine again it calls :meth:`from_state` methods.

        The returned state can be any picklable object. If it's None,
        the tab will not be restored at all after restarting, and by
        default, :meth:`get_state` always returns None.
        """
        return None

    @classmethod
    def from_state(cls, state):
        """Create a new tab from the return value of :meth:`get_state`.

        Be sure to override this if you override :meth:`get_state`.
        """
        raise NotImplementedError(
            "from_state() wasn't overrided but get_state() was overrided")


class FileTab(Tab):
    """A tab that represents an opened file.

    The tab will have content in it by default when it's opened. If
    *path* is given, the file will be saved there when Ctrl+S is
    pressed. Otherwise this becomes a "New File" tab.

    If you want to read a file and open a new tab from 

    .. virtualevent:: PathChanged

        This runs when :attr:`~path` is set to a new value. Use
        ``event.widget.path`` to get the new path.

    .. virtualevent:: FiletypeChanged

        Like :virtevt:`~PathChanged`, but for :attr:`~filetype`. Use
        ``event.widget.filetype`` to access the new file type.

    .. virtualevent:: Save

        This runs before the file is saved with the :meth:`save` method.

    .. attribute:: textwidget

        The central text widget of the tab.

        Currently this is a :class:`porcupine.textwidget.MainText`, but
        this is guaranteed to always be a
        :class:`HandyText <porcupine.textwidget.HandyText>`.

    .. attribute:: scrollbar

        This is the ``ttk.Scrollbar`` widget next to :attr:`.textwidget`.

        Things like :source:`the line number plugin <porcupine/plugins/linenum\
bers.py>` use this attribute.

    .. attribute:: path

        The path where this file is currently saved.

        This is None if the file has never been saved, and otherwise
        an absolute path as a string.

        .. seealso:: The :virtevt:`.PathChanged` virtual event.

    .. attribute:: filetype

        A value from :data:`porcupine.filetypes.filetypes`.

        .. seealso:: The :virtevt:`.FiletypeChanged` virtual event.
    """

    def __init__(self, manager, content='', path=None):
        super().__init__(manager)

        self._save_hash = None

        # path and filetype are set correctly below
        # TODO: try to guess the filetype from the content when path is None
        self._path = path
        self._guess_filetype()          # this sets self._filetype
        self.bind('<<PathChanged>>', self._update_title, add=True)
        self.bind('<<PathChanged>>', self._guess_filetype, add=True)

        # we need to set width and height to 1 to make sure it's never too
        # large for seeing other widgets
        # TODO: document this
        self.textwidget = textwidget.MainText(
            self, self._filetype, width=1, height=1, wrap='none', undo=True)
        self.textwidget.pack(side='left', fill='both', expand=True)
        self.bind('<<FiletypeChanged>>',
                  lambda event: self.textwidget.set_filetype(self.filetype),
                  add=True)
        self.textwidget.bind('<<ContentChanged>>', self._update_title,
                             add=True)

        if content:
            self.textwidget.insert('1.0', content)
            self.textwidget.edit_reset()   # reset undo/redo

        self.bind('<<PathChanged>>', self._update_status, add=True)
        self.bind('<<FiletypeChanged>>', self._update_status, add=True)
        self.textwidget.bind('<<CursorMoved>>', self._update_status, add=True)

        # everything seems to work ok without this except that e.g.
        # pressing Ctrl+O in the text widget opens a file AND inserts a
        # newline (Tk inserts a newline by default)
        utils.copy_bindings(porcupine.get_main_window(), self.textwidget)

        self.scrollbar = ttk.Scrollbar(self)
        self.scrollbar.pack(side='left', fill='y')
        self.textwidget['yscrollcommand'] = self.scrollbar.set
        self.scrollbar['command'] = self.textwidget.yview

        self.mark_saved()
        self._update_title()
        self._update_status()

    @classmethod
    def open_file(cls, manager, path):
        """Read a file and return a new FileTab object.

        Use this constructor if you want to open an existing file from a
        path and let the user edit it.

        :exc:`UnicodeError` or :exc:`OSError` is raised if reading the
        file fails.
        """
        config = settings.get_section('General')
        with open(path, 'r', encoding=config['encoding']) as file:
            content = file.read()
        return cls(manager, content, path)

    def equivalent(self, other):
        """Return True if *self* and *other* are saved to the same place.

        This method overrides :meth:`Tab.can_be_closed` and returns
        False if other is not a FileTab or the path of at least one of
        the tabs is None. If neither path is None, this returns True if
        the paths point to the same file. This way, it's possible to
        have multiple "New File" tabs.
        """
        # this used to have hasattr(other, "path") instead of isinstance
        # but it screws up if a plugin defines something different with
        # a path attribute, for example, a debugger plugin might have
        # tabs that represent files and they might need to be opened at
        # the same time as FileTabs are
        return (isinstance(other, FileTab) and
                self.path is not None and
                other.path is not None and
                os.path.samefile(self.path, other.path))

    def _get_hash(self):
        # superstitious omg-optimization
        config = settings.get_section('General')
        encoding = config['encoding']

        result = hashlib.md5()
        for chunk in self.textwidget.iter_chunks():
            chunk = chunk.encode(encoding, errors='replace')
            result.update(chunk)

        # hash objects don't define an __eq__ so we need to use a string
        # representation of the hash
        return result.hexdigest()

    def mark_saved(self):
        """Make :meth:`is_saved` return True."""
        self._save_hash = self._get_hash()
        self._update_title()      # TODO: add a virtual event for this?

    def is_saved(self):
        """Return False if the text has changed since previous save.

        This is set to False automagically when the content is modified.
        Use :meth:`mark_saved` to set this to True.
        """
        return self._get_hash() == self._save_hash

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, new_path):
        if self.path is None and new_path is None:
            it_changes = False
        elif self.path is None or new_path is None:
            it_changes = True
        else:
            # windows paths are case-insensitive
            it_changes = (os.path.normcase(self._path) !=
                          os.path.normcase(new_path))

        self._path = new_path
        if it_changes:
            self.event_generate('<<PathChanged>>')

    @property
    def filetype(self):
        return self._filetype

    @filetype.setter
    def filetype(self, filetype):
        assert filetype in filetypes.filetypes.values()
        self._filetype = filetype
        self.event_generate('<<FiletypeChanged>>')

    def _guess_filetype(self, junk=None):
        if self.path is None:
            # there's no way to "unsave a file", but a plugin might do
            # that for whatever reason
            self.filetype = filetypes.filetypes['Text only']
        else:
            self.filetype = filetypes.guess_filetype(self.path)

    def _update_title(self, junk=None):
        text = 'New File' if self.path is None else os.path.basename(self.path)
        if not self.is_saved():
            # TODO: figure out how to make the label red in ttk instead
            # of stupid stars
            text = '*' + text + '*'
        self.title = text

    def _update_status(self, junk=None):
        if self.path is None:
            start = "New file"
        else:
            start = "File '%s'" % self.path
        line, column = self.textwidget.index('insert').split('.')

        self.status = "%s, %s\tLine %s, column %s" % (
            start, self.filetype.name, line, column)

    def can_be_closed(self):
        """
        This overrides :meth:`Tab.can_be_closed` in order to display a
        save dialog.

        If the file has been saved, this returns True and the tab is
        closed normally. Otherwise this method asks the user whether the
        file should be saved, and returns False only if the user cancels
        something (and thus wants to keep working on this file).
        """
        if self.is_saved():
            return True

        if self.path is None:
            msg = "Do you want to save your changes?"
        else:
            msg = ("Do you want to save your changes to %s?"
                   % os.path.basename(self.path))
        answer = messagebox.askyesnocancel("Close file", msg)
        if answer is None:
            # cancel
            return False
        if answer:
            # yes
            return self.save()
        # no was clicked, can be closed
        return True

    # TODO: document the overriding
    def on_focus(self):
        self.textwidget.focus()

    # TODO: returning None on errors kinda sucks
    def save(self):
        """Save the file to the current :attr:`path`.

        This calls :meth:`save_as` if :attr:`path` is None, and returns
        False if the user cancels the save as dialog. None is returned
        on errors, and True is returned in all other cases. In other
        words, this returns True if saving succeeded.

        .. seealso:: The :virtevt:`Save` event.
        """
        if self.path is None:
            return self.save_as()

        self.event_generate('<<Save>>')

        encoding = settings.get_section('General')['encoding']
        try:
            with utils.backup_open(self.path, 'w', encoding=encoding) as f:
                for chunk in self.textwidget.iter_chunks():
                    f.write(chunk)
        except (OSError, UnicodeError) as e:
            log.exception("saving '%s' failed", self.path)
            utils.errordialog(type(e).__name__, "Saving failed!",
                              traceback.format_exc())
            return None

        self.mark_saved()
        return True

    def save_as(self):
        """Ask the user where to save the file and save it there.

        Returns True if the file was saved, and False if the user
        cancelled the dialog.
        """
        path = _dialogs.save_as(self.path)
        if path is None:
            return False
        self.path = path
        self.save()
        return True

    def get_state(self):
        if self.path is None:
            return None
        return (self.path, self.textwidget.index('insert'))

    @classmethod
    def from_state(cls, manager, state):
        path, cursor_pos = state
        tab = cls.open_file(manager, path)
        tab.textwidget.mark_set('insert', cursor_pos)
        tab.textwidget.see('insert')
        return tab


if __name__ == '__main__':
    # test/demo
    from porcupine.utils import _init_images
    root = tkinter.Tk()
    _init_images()

    tabmgr = TabManager(root)
    tabmgr.pack(fill='both', expand=True)
    tabmgr.bind('<<NewTab>>',
                lambda event: print("added tab", event.data_widget.i),
                add=True)
    tabmgr.bind('<<CurrentTabChanged>>',
                lambda event: print("selected", event.widget.current_tab.i),
                add=True)

    def on_ctrl_w(event):
        if tabmgr.tabs:    # current_tab is not None
            tabmgr.close_tab(tabmgr.current_tab)

    root.bind('<Control-w>', on_ctrl_w)
    for keysym, callback in tabmgr.bindings:
        root.bind(keysym, callback)

    def add_new_tab(counter=itertools.count(1)):
        tab = Tab(tabmgr)
        tab.i = next(counter)     # tabmgr doesn't care about this
        tab.title = "tab %d" % tab.i
        tabmgr.add_tab(tab)

        text = tkinter.Text(tab)
        text.pack()
        text.insert('1.0', "this is the content of tab %d" % tab.i)

    ttk.Button(root, text="add a new tab", command=add_new_tab).pack()
    add_new_tab(), add_new_tab(), add_new_tab(), add_new_tab(), add_new_tab()
    root.geometry('300x200')
    root.mainloop()
