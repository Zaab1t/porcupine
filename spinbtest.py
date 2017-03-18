import tkinter as tk
from tkinter import ttk


try:
    # There's no ttk.Spinbox for some reason. Maybe this will be fixed
    # later?
    TtkSpinbox = ttk.Spinbox
except AttributeError:
    # At least not yet, but implementing this is easy to do by reading
    # the code of ttk.Combobox
    class TtkSpinbox(ttk.Entry):

        def __init__(self, master=None, *, from_=None, **kwargs):
            if from_ is not None:
                kwargs['from'] = from_  # this actually works
            super().__init__(master, 'ttk::spinbox', **kwargs)


root = tk.Tk()
spinb = TtkSpinbox(root, from_=0, to=10)
spinb.pack()
root.mainloop()
