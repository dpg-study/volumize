#!/usr/bin/env python3
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from config import Config


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("3D Reconstruction Studio")
        self.geometry("1200x800")
        self.minsize(1000, 600)

        # Создаем меню
        self.create_menu()

        # Создаем главное окно
        self.main_window = MainWindow(self)
        self.main_window.pack(fill=tk.BOTH, expand=True)

        # Обработка закрытия
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Статус бар
        self.status_bar = ttk.Label(self, text="Готов к работе", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_menu(self):
        """Создание меню приложения"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)

        file_menu.add_command(label="Выбрать папку с фото",
                              command=lambda: self.main_window.select_folder())

        file_menu.add_command(label="Открыть модель",
                              command=lambda: self.main_window.show_model())

        file_menu.add_separator()

        file_menu.add_command(label="Преобразовать облако точек в 3D модель",
                              command=lambda: self.main_window.open_mesh_dialog())

        file_menu.add_separator()

        file_menu.add_command(label="Выход", command=self.on_closing)

        # Меню Помощь
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)

        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Инструкция", command=self.show_help)

    def show_about(self):
        """О программе"""
        about_text = """3D Reconstruction Studio\n\nВерсия: 1.0.0\nТехнологии:\n- COLMAP\n- Open3D\n- Python/Tkinter"""
        messagebox.showinfo("О программе", about_text)

    def show_help(self):
        """Инструкция"""
        help_text = """ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ:

1. РЕКОНСТРУКЦИЯ ПО ФОТО:
   - Сделайте 20-50 фото объекта со всех сторон
   - Нажмите "Обзор" и выберите папку с фото
   - Нажмите "Запустить реконструкцию"
   - Дождитесь завершения

2. ПРОСМОТР МОДЕЛИ:
   - Нажмите "Показать модель"
   - Вращайте мышью

3. ПРЕОБРАЗОВАНИЕ В 3D МОДЕЛЬ:
   - Нажмите "🔨 Облако точек → 3D модель"
   - Выберите PLY файл
   - Нажмите "Создать 3D-модель"
"""
        messagebox.showinfo("Инструкция", help_text)

    def on_closing(self):
        """Обработка закрытия"""
        if hasattr(self.main_window, 'on_closing'):
            self.main_window.on_closing()

        if hasattr(self.main_window, 'colmap_runner') and self.main_window.colmap_runner.is_running:
            if messagebox.askokcancel("Выход", "Реконструкция еще выполняется. Остановить и выйти?"):
                self.main_window.stop_reconstruction()
                self.destroy()
        else:
            self.destroy()


if __name__ == "__main__":
    app = Application()
    app.mainloop()