from gui_sim import LockerSimulator
import tkinter as tk

def main():
    root = tk.Tk()
    app = LockerSimulator(root)
    root.mainloop()

if __name__ == "__main__":
    main()