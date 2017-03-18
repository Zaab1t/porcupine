import tkinter as tk




if __name__ == '__main__':
    root = tk.Tk()
    checkb = create_checkbox(root, text="check me bitch")
    checkb.pack()
    checkb.on_check.append(print)
    root.mainloop()
