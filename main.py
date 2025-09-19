# main.py
import tkinter as tk
from gui.gui import CSVPosterGUI


def main():
    root = tk.Tk()
    app = CSVPosterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
