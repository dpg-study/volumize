# !/usr/bin/env python3
# -*- coding: utf-8 -*-

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

        self.title("3D Reconstruction Studio - COLMAP + Tiny3D")
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
        file_menu.add_command(label="Выбрать папку с фото",
                              command=lambda: self.main_window.select_folder())
        file_menu.add_command(label="Открыть модель",
                              command=lambda: self.main_window.show_model())
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_closing)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Сбросить вид",
                              command=lambda: self.main_window.viewer.reset_view())

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Инструкция", command=self.show_help)

    def show_about(self):

        about_text = """3D Reconstruction Studio

Версия: 1.0.0
Технологии:
- COLMAP (фотограмметрия)
- tiny-3d-engine (визуализация)
- Python/Tkinter

Разработано для создания 3D-моделей
из фотографий"""

        messagebox.showinfo("О программе", about_text)

    def show_help(self):

        help_text = """Инструкция по использованию:

1. Сделайте 20-50 фотографий объекта со всех сторон
2. Нажмите "Обзор" и выберите папку с фото
3. Нажмите "Запустить реконструкцию"
4. Дождитесь завершения (может занять 10-30 минут)
5. Наслаждайтесь 3D-моделью!

Советы:
- Фото должны иметь 60-70% перекрытия
- Избегайте бликов и теней
- Используйте штатив для резкости"""

        messagebox.showinfo("Инструкция", help_text)

    def on_closing(self):

        if self.main_window.colmap_runner.is_running:
            if messagebox.askokcancel("Выход",
                                      "Реконструкция еще выполняется. Остановить и выйти?"):
                self.main_window.stop_reconstruction()
                self.destroy()
        else:
            self.destroy()


if __name__ == "__main__":
    app = Application()
    app.mainloop()
