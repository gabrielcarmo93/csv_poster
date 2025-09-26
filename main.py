# main.py
import ttkbootstrap as ttk
from gui.gui import CSVPosterGUI


def main():
    # Criar janela principal com tema do ttkbootstrap
    root = ttk.Window(
        title="CSV to API Poster",
        themename="darkly",
        resizable=(True, True),
        size=(1000, 900)
    )
    
    app = CSVPosterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
