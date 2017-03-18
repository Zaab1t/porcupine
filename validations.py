def _is_valid_encoding(name):
    try:
        codecs.lookup(name)
        return True
    except LookupError:
        return False


def _is_valid_font(string):
    try:
        tkfont.Font(font=name)
        return True
    except tk.TclError:
        return False


def _is_valid_theme(name):
    return name in color_themes


def _is_valid_geometry(geometry):
    """Check if a tkinter geometry is valid.

    >>> _is_valid_geometry('100x200+300+400')
    True
    >>> _is_valid_geometry('100x200')
    True
    >>> _is_valid_geometry('+300+400')
    True
    >>> _is_valid_geometry('asdf')
    False
    >>> # tkinter actually allows '', but it does nothing
    >>> _is_valid_geometry('')
    False
    """
    if not geometry:
        return False
    return re.search(r'^(\d+x\d+)?(\+\d+\+\d+)?$', geometry) is not None
