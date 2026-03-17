import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from PIL import Image, ImageTk

from core.colmap_runner import COLMAPRunner
from gui.real_3d_viewer import Real3DViewer
from config import Config


class MainWindow(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config = Config()
        self.colmap_runner = COLMAPRunner(self.config)
        self.current_project_dir = None

        self.setup_ui()
        self.check_colmap()

    def setup_ui(self):
        """Создание интерфейса"""

        # Верхняя панель с настройками
        self.create_top_panel()

        # Панель с вкладками (вьювер и лог)
        self.create_tabs()

        # Нижняя панель с прогрессом
        self.create_progress_bar()

    def create_top_panel(self):
        """Панель выбора фотографий и запуска"""
        top_frame = ttk.LabelFrame(self, text="Настройки", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # Выбор папки с фото
        ttk.Label(top_frame, text="Папка с фотографиями:").grid(row=0, column=0, sticky=tk.W, pady=5)

        self.folder_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.folder_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(top_frame, text="Обзор...", command=self.select_folder).grid(row=0, column=2)

        # Информация о количестве фото
        self.photos_count_label = ttk.Label(top_frame, text="Нет фото")
        self.photos_count_label.grid(row=1, column=1, sticky=tk.W, pady=5)

        # Кнопки управления
        button_frame = ttk.Frame(top_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)

        self.start_btn = ttk.Button(button_frame, text="▶ Запустить реконструкцию",
                                    command=self.start_reconstruction, state='disabled')
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="⏹ Остановить",
                                   command=self.stop_reconstruction, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Кнопка просмотра результата
        self.view_btn = ttk.Button(button_frame, text="👁 Показать модель",
                                   command=self.show_model, state='disabled')
        self.view_btn.pack(side=tk.LEFT, padx=5)

        # НОВАЯ КНОПКА: конвертация облака точек в mesh
        convert_btn = ttk.Button(button_frame, text="🔨 Облако точек → 3D модель",
                                 command=self.open_mesh_dialog)
        convert_btn.pack(side=tk.LEFT, padx=5)

    def create_tabs(self):
        """Создание вкладок для 3D-вьювера и лога"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Вкладка с 3D-вьювером
        viewer_tab = ttk.Frame(self.notebook)
        self.notebook.add(viewer_tab, text="🖥 3D Просмотр")

        # Создаем настоящий 3D-вьювер
        self.viewer = Real3DViewer(viewer_tab, self.config)

        # Вкладка с логом
        log_tab = ttk.Frame(self.notebook)
        self.notebook.add(log_tab, text="📋 Лог выполнения")

        # Текстовое поле для лога
        self.log_text = tk.Text(log_tab, wrap=tk.WORD, bg='#1e1e1e', fg='#d4d4d4')
        scrollbar = ttk.Scrollbar(log_tab, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_progress_bar(self):
        """Прогресс-бар внизу окна"""
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack(side=tk.RIGHT, padx=5)

    def check_colmap(self):
        """Проверка наличия COLMAP"""
        colmap_path = self.config.get_colmap_path()
        if colmap_path:
            self.log(f"✅ COLMAP найден: {colmap_path}")
        else:
            self.log("❌ COLMAP не найден! Реконструкция невозможна.")
            messagebox.showwarning("Предупреждение",
                                   "COLMAP не найден. Реконструкция невозможна.")

    def select_folder(self):
        """Выбор папки с фотографиями"""
        folder = filedialog.askdirectory(title="Выберите папку с фотографиями")
        if folder:
            self.folder_var.set(folder)
            self.check_photos(folder)

    def check_photos(self, folder):
        """Проверяет наличие фотографий в папке"""
        valid_extensions = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')
        photos = [f for f in os.listdir(folder)
                  if f.lower().endswith(valid_extensions)]

        count = len(photos)
        self.photos_count_label.config(text=f"Найдено фото: {count}")

        if count >= self.config.MIN_PHOTOS:
            self.start_btn.config(state='normal')
            self.log(f"✅ Достаточно фото для реконструкции ({count} шт.)")
        else:
            self.start_btn.config(state='disabled')
            self.log(f"❌ Слишком мало фото: {count}. Нужно минимум {self.config.MIN_PHOTOS}")

        # Показываем первые несколько фото в логе
        if photos:
            self.log(f"📸 Примеры: {', '.join(photos[:5])}")

    def start_reconstruction(self):
        """Запуск реконструкции"""
        folder = self.folder_var.get()

        if not folder or not os.path.exists(folder):
            self.log("❌ Ошибка: папка с фото не существует")
            return

        # Нормализуем путь
        folder = os.path.normpath(folder)

        # Создаем папку для проекта
        project_name = os.path.basename(folder)
        self.current_project_dir = os.path.join(
            os.path.dirname(folder),
            f"{project_name}_3d_model"
        )
        self.current_project_dir = os.path.normpath(self.current_project_dir)
        os.makedirs(self.current_project_dir, exist_ok=True)

        self.log(f"📁 Создана папка для результатов: {self.current_project_dir}")

        # Проверяем COLMAP
        colmap_path = self.config.get_colmap_path()
        if not colmap_path:
            self.log("❌ COLMAP не найден! Реконструкция невозможна.")
            messagebox.showerror("Ошибка", "COLMAP не найден!")
            return

        self.log(f"✅ COLMAP найден: {colmap_path}")
        self.log(f"📁 Фото: {folder}")
        self.log(f"📁 Результат: {self.current_project_dir}")

        # Проверяем фото
        valid_extensions = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
        photos = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        if len(photos) < self.config.MIN_PHOTOS:
            self.log(f"❌ Слишком мало фото: {len(photos)}")
            messagebox.showerror("Ошибка", f"Слишком мало фото: {len(photos)}")
            return

        self.log(f"📸 Найдено фото: {len(photos)}")
        self.log(f"📸 Примеры: {', '.join(photos[:5])}")

        # Обновляем UI
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.view_btn.config(state='disabled')
        self.progress.start()
        self.progress_label.config(text="Реконструкция...")

        self.log("=" * 50)
        self.log("🚀 НАЧАЛО РЕКОНСТРУКЦИИ")
        self.log("=" * 50)

        # Запускаем в отдельном потоке
        def run_thread():
            def ui_callback(msg, progress=None):
                self.parent.after(0, self.log, msg)
                if progress is not None:
                    self.parent.after(0, self.update_progress, progress)

            success = self.colmap_runner.run_full_pipeline(
                folder,
                self.current_project_dir,
                ui_callback
            )

            if success:
                ply_file = os.path.join(self.current_project_dir, "dense", "fused.ply")
                if os.path.exists(ply_file):
                    self.parent.after(0, self.reconstruction_complete, ply_file)
                else:
                    self.parent.after(0, self.reconstruction_failed, "PLY файл не найден")
            else:
                self.parent.after(0, self.reconstruction_failed, "Ошибка в процессе")

        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()

    def reconstruction_complete(self, ply_file):
        """Обработка успешного завершения"""
        self.progress.stop()
        self.progress_label.config(text="Готово!")
        self.stop_btn.config(state='disabled')
        self.view_btn.config(state='normal')

        self.log("✅" * 10)
        self.log("✅ РЕКОНСТРУКЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        self.log(f"📁 Модель: {ply_file}")
        self.log("✅" * 10)

        if os.path.exists(ply_file):
            file_size = os.path.getsize(ply_file) / (1024 * 1024)
            self.log(f"📊 Размер файла: {file_size:.2f} МБ")

            if messagebox.askyesno("Готово", f"Реконструкция завершена!\nПоказать 3D-модель?"):
                self.show_model(ply_file)

    def reconstruction_failed(self, error_msg):
        """Обработка ошибки"""
        self.progress.stop()
        self.progress_label.config(text="Ошибка")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        self.log(f"❌ ОШИБКА: {error_msg}")
        messagebox.showerror("Ошибка", f"Реконструкция не удалась:\n{error_msg}")

    def show_model(self, ply_file=None):
        """Показывает 3D-модель во вьювере"""
        if ply_file is None:
            ply_file = filedialog.askopenfilename(
                title="Выберите PLY файл",
                filetypes=[("PLY files", "*.ply")]
            )
            if not ply_file:
                return

        # Переключаемся на вкладку с вьювером
        self.notebook.select(0)

        # Загружаем в Real3DViewer
        self.viewer.load_model(ply_file)
        self.log(f"👁 Загружена модель: {ply_file}")

    def open_mesh_dialog(self):
        """Открывает диалог конвертации облака точек в mesh"""
        try:
            from gui.mesh_dialog import MeshDialog
            MeshDialog(self.parent)
        except ImportError as e:
            self.log(f"❌ Ошибка: не удалось загрузить диалог конвертации: {e}")
            messagebox.showerror("Ошибка", "Модуль mesh_dialog не найден. Проверьте файл gui/mesh_dialog.py")

    def stop_reconstruction(self):
        """Остановка процесса"""
        if self.colmap_runner:
            self.colmap_runner.stop()
            self.log("⛔ Процесс остановлен пользователем")

        self.progress.stop()
        self.progress_label.config(text="Остановлено")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def update_progress(self, value):
        """Обновление прогресса"""
        self.progress_label.config(text=f"Выполнено: {value}%")

    def log(self, message):
        """Добавление сообщения в лог"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.parent.update_idletasks()

    def on_closing(self):
        """Закрытие вьювера при выходе"""
        if hasattr(self, 'viewer'):
            self.viewer.close()