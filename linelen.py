import tkinter as tk
import tkinter.font as tkfont


class LineLengthMarker:

    def __init__(self, textwidget, where):
        font = tkfont.Font(font=textwidget['font'])
        location = font.measure(' ') * where
        textwidget.bind('<Configure>', self._on_configure)

        self._frame = tk.Frame(textwidget, width=1, bg='red')
        self._frame.place(x=location)

    def _on_configure(self, event):
        self._frame.place(height=event.height)


if __name__ == '__main__':
    root = tk.Tk()
    text = tk.Text(root)
    text.pack()#fill='both', expand=True)
    marker = LineLengthMarker(text, -1)
    root.mainloop()
