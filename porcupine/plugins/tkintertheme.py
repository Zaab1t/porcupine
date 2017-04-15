"""Make all Tk widgets look like Porcupine's theme."""

from porcupine import config, plugins, utils


def session_hook(editor):
    old_color = utils.get_root()['bg']

    @config.connect('general', 'color_theme')
    def set_theme(name):
        color = config.color_themes[name]['background']
        utils.get_root().tk_setPalette(color)

    try:
        yield
    finally:
        config.disconnect('general', 'color_theme', set_theme)
        utils.get_root().tk_setPalette(old_color)


plugins.add_plugin("Tk Theme", session_hook=session_hook)
