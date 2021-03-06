# note about virtual events: sometimes running any_widget.update()
# before generating a virtual event is needed for the virtual event to
# actually do something, if you have weird problems with tests try
# adding any_widget.update() calls
# see also update(3tcl)

import atexit
import shutil
import tempfile
import tkinter

import pytest

# these must be after the above hack
from porcupine import _session, dirs, get_main_window, get_tab_manager
from porcupine import filetypes as filetypes_module

# TODO: something else will be needed when testing the filetypes
tempdir = tempfile.mkdtemp()
dirs.configdir = tempdir
atexit.register(shutil.rmtree, tempdir)
del tempdir


@pytest.fixture(scope='session')
def porcusession():
    # these errors should not occur after the init
    with pytest.raises(RuntimeError):
        get_main_window()

    with pytest.raises(RuntimeError):
        get_tab_manager()

    root = tkinter.Tk()
    root.withdraw()
    _session.init(root)
    yield
    _session.quit()


@pytest.fixture(scope='session')
def filetypes(porcusession):
    filetypes_module._init()
    return filetypes_module   # avoid importing as filetypes_module elsewhere


@pytest.fixture
def tabmanager(porcusession):
    assert not get_tab_manager().tabs, "something hasn't cleaned up its tabs"
    yield get_tab_manager()
    assert not get_tab_manager().tabs, "the test didn't clean up its tabs"
