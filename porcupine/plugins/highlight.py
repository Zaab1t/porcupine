"""Syntax highlighting for Tkinter's text widget with Pygments."""
# FIXME: highlight the whole file when e.g. pasting
# FIXME: multiline strings and comments break everything if you add a
#        terminator character in the middle of the multi-line shit :/
# TODO: better support for different languages in the rest of the editor

import re
import tkinter.font as tkfont

import pygments.styles
import pygments.token
import pygments.util   # only for ClassNotFound, the docs say that it's here

import porcupine
from porcupine import settings, tabs

config = settings.get_section('General')


def _list_all_token_types(tokentype):
    yield tokentype
    for sub in map(_list_all_token_types, tokentype.subtypes):
        yield from sub

_ALL_TAGS = set(map(str, _list_all_token_types(pygments.token.Token)))  # noqa


def tokenize(lexer, code, first_lineno):
    lineno, column = first_lineno, 0

    # pygments skips empty lines in the beginning
    lineno += len(re.search(r'^\n*', code).group(0))

    for tokentype, text in lexer.get_tokens(code):
        start = (lineno, column)
        if '\n' in text:
            lineno += text.count('\n')
            column = len(text.split('\n')[-1])
        else:
            column += len(text)
        end = (lineno, column)
        yield tokentype, start, end


class Highlighter:

    def __init__(self, textwidget, lexer_getter):
        self.textwidget = textwidget
        self._get_lexer = lexer_getter

        # the tags use fonts from here
        self._fonts = {}
        for bold in (True, False):
            for italic in (True, False):
                # the fonts will be updated later, see _on_config_changed()
                self._fonts[(bold, italic)] = tkfont.Font(
                    weight=('bold' if bold else 'normal'),
                    slant=('italic' if italic else 'roman'))

        config.connect('pygments_style', self._on_config_changed)
        config.connect('font_family', self._on_config_changed)
        config.connect('font_size', self._on_config_changed)
        self._on_config_changed()

        textwidget.bind('<Destroy>', self.on_destroy, add=True)

    def on_destroy(self, junk=None):
        config.disconnect('pygments_style', self._on_config_changed)
        config.disconnect('font_family', self._on_config_changed)
        config.disconnect('font_size', self._on_config_changed)

    def _on_config_changed(self, junk=None):
        font_updates = tkfont.Font(name='TkFixedFont', exists=True).actual()
        del font_updates['weight']     # ignore boldness
        del font_updates['slant']      # ignore italicness

        for (bold, italic), font in self._fonts.items():
            # fonts don't have an update() method
            for key, value in font_updates.items():
                font[key] = value

        # http://pygments.org/docs/formatterdevelopment/#styles
        # all styles seem to yield all token types when iterated over, so
        # we should always end up with the same tags configured
        style = pygments.styles.get_style_by_name(config['pygments_style'])
        for tokentype, infodict in style:
            # this doesn't use underline and border
            # i don't like random underlines in my code and i don't know
            # how to implement the border with tkinter
            key = (infodict['bold'], infodict['italic'])   # pep8 line length
            kwargs = {'font': self._fonts[key]}

            if infodict['color'] is None:
                kwargs['foreground'] = ''    # reset it
            else:
                kwargs['foreground'] = '#' + infodict['color']

            if infodict['bgcolor'] is None:
                kwargs['background'] = ''
            else:
                kwargs['background'] = '#' + infodict['bgcolor']

            # tag_lower makes sure that the selection tag shows above
            # our token tag
            self.textwidget.tag_config(str(tokentype), **kwargs)
            self.textwidget.tag_lower(str(tokentype), 'sel')

    def _in_middle_of_tag(self, index):
        for tag in self.textwidget.tag_names(index):
            if (tag.startswith('Token.') and not
                    tag.startswith(('Token.Text', 'Token.Text.'))):
                # usually Token.Text means whitespace or something else
                # that doesn't need to be highlighted
                return True
        return False

    def _highlight_range(self, start_lineno, end_lineno):
        print(start_lineno, end_lineno)

        for tag in self.textwidget.tag_names():
            if tag.startswith('Token.'):
                self.textwidget.tag_remove(tag, '%d.0' % start_lineno,
                                           '%d.0' % end_lineno)

        code = self.textwidget.get('%d.0' % start_lineno, '%d.0' % end_lineno)
        tokens = tokenize(self._get_lexer(), code, start_lineno)
        for tokentype, start, end in tokens:
            self.textwidget.tag_add(str(tokentype), '%d.%d' % start,
                                    '%d.%d' % end)

    def highlight_around(self, lineno):
        # find a 10 line chunk of code around the given lineno
        start_lineno = max(lineno // 10 * 10, 1)
        end_lineno = start_lineno + 10

        # try to avoid bugs, with fingers crossed...
        while (start_lineno > 1 and
               self._in_middle_of_tag('%d.0 - 1 char' % start_lineno)):
            start_lineno -= 10
        if start_lineno < 1:
            start_lineno = 1

        # lineno_max goes *past* the last line, so '%d.0' % lineno_max is
        # the end of the text widget
        lineno_max = int(self.textwidget.index('end').split('.')[0])
        while (lineno_max < lineno_max and
               self._in_middle_of_tag('%d.0' % end_lineno)):
            end_lineno += 10
        if end_lineno > lineno_max:
            end_lineno = lineno_max

        self._highlight_range(start_lineno, end_lineno)

    def highlight_around_cursor(self, junk=None):
        cursor_lineno = int(self.textwidget.index('insert').split('.')[0])
        self.highlight_around(cursor_lineno)

    def highlight_all(self, junk=None):
        lineno_max = int(self.textwidget.index('end').split('.')[0])
        self._highlight_range(1, lineno_max)


def on_new_tab(event):
    tab = event.widget.tabs[-1]
    if not isinstance(tab, tabs.FileTab):
        return

    highlighter = Highlighter(
        tab.textwidget, (lambda: tab.filetype.get_lexer()))
    tab.bind('<<FiletypeChanged>>', highlighter.highlight_all, add=True)
    tab.textwidget.bind(
        '<<ContentChanged>>', highlighter.highlight_around_cursor,   # FIXME
        add=True)
    highlighter.highlight_all()


def setup():
    porcupine.get_tab_manager().bind('<<NewTab>>', on_new_tab, add=True)


if __name__ == '__main__':
    # simple test
    import tkinter

    def on_modified(event):
        text.unbind('<<Modified>>')
        text.edit_modified(False)
        text.bind('<<Modified>>', on_modified)

        cursor_lineno = int(event.widget.index('insert').split('.')[0])
        highlighter.highlight_around(cursor_lineno)

    root = tkinter.Tk()
    config = settings.get_section('General')
    text = tkinter.Text(root, insertbackground='red')
    text.pack(fill='both', expand=True)
    text.bind('<<Modified>>', on_modified)

    # The theme doesn't display perfectly here because the highlighter
    # only does tags, not foreground, background etc. See textwidget.py.
    highlighter = Highlighter(text, (lambda: 'Python'))

    with open(__file__, 'r') as f:
        text.insert('1.0', f.read())
    text.see('end')

    try:
        root.mainloop()
    finally:
        highlighter.on_destroy()
