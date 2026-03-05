import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from config import Config

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("3D Reconstruction Studio")
        self.geometry("1200x800")
        self.minsize(1000, 600)
        try:
            self.iconbitmap("assets/icon.ico")
        except:
            pass
        self.create_menu()
        self.main_window = MainWindow(self)
        self.main_window.pack(fill=tk.BOTH, expand=True)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.status_bar = ttk.Label(self, text="Готов к работе", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Выход", command=self.on_closing)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Инструкция", command=self.show_help)

    def show_about(self):
        about_text = "3D Reconstruction Studio\n\nВерсия: 1.0.0\nТехнологии:\n- COLMAP\n- tiny-3d-engine\n- Python/Tkinter"
        messagebox.showinfo("О программе", about_text)

    def show_help(self):
        help_text = "Инструкция:\n\n1. Выберите папку с фото\n2. Нажмите Запустить реконструкцию\n3. Дождитесь завершения"
        messagebox.showinfo("Инструкция", help_text)

    def on_closing(self):
        if self.main_window.colmap_runner and self.main_window.colmap_runner.is_running:
            if messagebox.askokcancel("Выход", "Процесс запущен. Прервать?"):
                self.main_window.colmap_runner.stop()
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = Application()
    app.mainloop()