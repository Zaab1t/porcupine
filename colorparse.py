import re


def parse_color(string):
    """Parse a '#RRGGBB style ...' string, e.g. '#ff0000 bold'.

    Return a (color, bold, italic, underline) tuple or raise ValueError.
    """
    color, *styles = string.lower().split()     # raises ValueError
    # the color can contain any number disible by 3 of hexadecimal
    # digits, e.g. '#f00' and '#ff0000' do the same thing
    if len(color) % 3 != 1 or not color.startswith('#'):
        raise ValueError("invalid color/style string %r" % string)

    styles = dict.fromkeys(styles, True)
    bold = styles.pop('bold', False)
    italic = styles.pop('italic', False)
    underline = styles.pop('underline', False)
    if styles:
        raise ValueError("invalid color/style string %r" % string)

    return (color, bold, italic, underline)
