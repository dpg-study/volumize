import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading

from core.colmap_runner import COLMAPRunner
from gui.real_3d_viewer import Real3DViewer
from gui.styles import setup_styles
from config import Config


class MainWindow(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config = Config()
        self.colmap_runner = COLMAPRunner(self.config)
        self.current_project_dir = None

        # Настройка стилей
        setup_styles()
        self.setup_ui()
        self.check_colmap()

    def setup_ui(self):
        """Создание интерфейса"""

        # Основной контейнер с отступами
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Разделяем на левую панель (управление) и правую (вьювер)
        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Левая панель управления
        left_panel = ttk.Frame(paned, width=400)
        paned.add(left_panel, weight=0)

        # Правая панель с вьювером
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=3)

        # Заполняем левую панель
        self.create_control_panel(left_panel)

        # Заполняем правую панель (вьювер)
        self.create_viewer_panel(right_panel)

        # Нижняя панель с прогрессом
        self.create_progress_bar(main_container)

    def create_control_panel(self, parent):
        """Создание панели управления"""

        # Карточка с настройками проекта
        project_card = ttk.LabelFrame(parent, text="Проект", padding=15)
        project_card.pack(fill=tk.X, pady=(0, 10))

        # Выбор папки с фото
        ttk.Label(project_card, text="Папка с фотографиями:").pack(anchor=tk.W, pady=(0, 5))

        folder_frame = ttk.Frame(project_card)
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        self.folder_var = tk.StringVar()
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var)
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(folder_frame, text="Обзор", command=self.select_folder, width=8).pack(side=tk.RIGHT)

        # Информация о фото
        info_frame = ttk.Frame(project_card)
        info_frame.pack(fill=tk.X)

        self.photos_count_label = ttk.Label(info_frame, text="Нет фото")
        self.photos_count_label.pack(side=tk.LEFT)

        # Карточка с действиями
        actions_card = ttk.LabelFrame(parent, text="Действия", padding=15)
        actions_card.pack(fill=tk.X, pady=(0, 10))

        # Кнопки действий
        button_grid = ttk.Frame(actions_card)
        button_grid.pack(fill=tk.X)

        # Первый ряд кнопок
        row1 = ttk.Frame(button_grid)
        row1.pack(fill=tk.X, pady=2)

        self.start_btn = ttk.Button(row1, text="Запустить реконструкцию",
                                    command=self.start_reconstruction, state='disabled',
                                    style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.stop_btn = ttk.Button(row1, text="Остановить",
                                   command=self.stop_reconstruction, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Второй ряд кнопок
        row2 = ttk.Frame(button_grid)
        row2.pack(fill=tk.X, pady=2)

        self.view_btn = ttk.Button(row2, text="Показать модель",
                                   command=self.show_model, state='disabled')
        self.view_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        ttk.Button(row2, text="Облако в модель",
                   command=self.open_mesh_dialog).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Карточка с настройками COLMAP
        settings_card = ttk.LabelFrame(parent, text="Параметры COLMAP", padding=15)
        settings_card.pack(fill=tk.X, pady=(0, 10))

        # Параметры как чекбоксы
        self.use_gpu_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_card, text="Использовать GPU (ускорение)",
                        variable=self.use_gpu_var).pack(anchor=tk.W, pady=2)

        self.dense_recon_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_card, text="Плотная реконструкция (качество)",
                        variable=self.dense_recon_var).pack(anchor=tk.W, pady=2)

        # Слайдер качества
        quality_frame = ttk.Frame(settings_card)
        quality_frame.pack(fill=tk.X, pady=5)

        ttk.Label(quality_frame, text="Качество:").pack(side=tk.LEFT)
        self.quality_var = tk.IntVar(value=50)
        quality_scale = ttk.Scale(quality_frame, from_=1, to=100,
                                  orient=tk.HORIZONTAL, variable=self.quality_var)
        quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Карточка со структурой проекта
        tree_card = ttk.LabelFrame(parent, text="Структура проекта", padding=15)
        tree_card.pack(fill=tk.BOTH, expand=True)

        # Список файлов
        self.tree_listbox = tk.Listbox(tree_card, bg='#404040', fg='white',
                                       selectbackground='#0078d4', borderwidth=0)
        self.tree_listbox.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.tree_listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_viewer_panel(self, parent):
        """Создание панели с 3D-вьювером"""
        # Создаем вьювер прямо в родительском фрейме
        self.viewer = Real3DViewer(parent, self.config, embedded=True)

    def create_progress_bar(self, parent):
        """Создание панели прогресса"""
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=(10, 0))

        # Прогресс-бар
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate',
                                        style='Horizontal.TProgressbar')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Метка прогресса
        self.progress_label = ttk.Label(progress_frame, text="", width=15)
        self.progress_label.pack(side=tk.RIGHT, padx=(10, 0))

        # Панель с логом
        self.create_log_panel(parent)

    def create_log_panel(self, parent):
        """Создание панели с логом"""
        log_frame = ttk.LabelFrame(parent, text="Лог выполнения", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Текстовое поле для лога
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_container, wrap=tk.WORD,
                                bg='#1e1e1e', fg='#d4d4d4',
                                font=('Consolas', 9),
                                borderwidth=0,
                                padx=5, pady=5)
        scrollbar = ttk.Scrollbar(log_container, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log("Добро пожаловать в Volumize!")
        self.log("Выберите папку с фотографиями для начала работы")

    def check_colmap(self):
        """Проверка наличия COLMAP"""
        colmap_path = self.config.get_colmap_path()
        if colmap_path:
            self.log(f"COLMAP найден: {colmap_path}")
        else:
            self.log("COLMAP не найден! Реконструкция невозможна.")
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
            self.log(f"Достаточно фото для реконструкции ({count} шт.)")
        else:
            self.start_btn.config(state='disabled')
            self.log(f"Слишком мало фото: {count}. Нужно минимум {self.config.MIN_PHOTOS}")

        if photos:
            self.log(f"Примеры: {', '.join(photos[:3])}")

    def start_reconstruction(self):
        """Запуск реконструкции"""
        folder = self.folder_var.get()

        if not folder or not os.path.exists(folder):
            self.log("Ошибка: папка с фото не существует")
            return

        folder = os.path.normpath(folder)

        project_name = os.path.basename(folder)
        self.current_project_dir = os.path.join(
            os.path.dirname(folder),
            f"{project_name}_3d_model"
        )
        self.current_project_dir = os.path.normpath(self.current_project_dir)
        os.makedirs(self.current_project_dir, exist_ok=True)

        self.log(f"Создана папка для результатов: {self.current_project_dir}")

        colmap_path = self.config.get_colmap_path()
        if not colmap_path:
            self.log("COLMAP не найден! Реконструкция невозможна.")
            messagebox.showerror("Ошибка", "COLMAP не найден!")
            return

        # Обновляем параметры в конфиге
        self.config.use_gpu = self.use_gpu_var.get()
        self.config.dense_reconstruction = self.dense_recon_var.get()
        self.config.quality = self.quality_var.get()

        self.log(f"COLMAP найден: {colmap_path}")
        self.log(f"Параметры: GPU={'да' if self.use_gpu_var.get() else 'нет'}, "
                 f"Плотная={'да' if self.dense_recon_var.get() else 'нет'}")

        photos = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        if len(photos) < self.config.MIN_PHOTOS:
            self.log(f"Слишком мало фото: {len(photos)}")
            messagebox.showerror("Ошибка", f"Слишком мало фото: {len(photos)}")
            return

        self.log(f"Найдено фото: {len(photos)}")

        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.view_btn.config(state='disabled')
        self.progress.start(10)
        self.progress_label.config(text="Реконструкция...")

        self.log("=" * 50)
        self.log("НАЧАЛО РЕКОНСТРУКЦИИ")
        self.log("=" * 50)

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

        self.log("=" * 50)
        self.log("РЕКОНСТРУКЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        self.log(f"Модель: {ply_file}")
        self.log("=" * 50)

        if os.path.exists(ply_file):
            file_size = os.path.getsize(ply_file) / (1024 * 1024)
            self.log(f"Размер файла: {file_size:.2f} МБ")

            if messagebox.askyesno("Готово", f"Реконструкция завершена!\nПоказать 3D-модель?"):
                self.show_model(ply_file)

    def reconstruction_failed(self, error_msg):
        """Обработка ошибки"""
        self.progress.stop()
        self.progress_label.config(text="Ошибка")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        self.log(f"ОШИБКА: {error_msg}")
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

        self.viewer.load_model(ply_file)
        self.log(f"Загружена модель: {ply_file}")

    def open_mesh_dialog(self):
        """Открывает диалог конвертации облака точек в mesh"""
        try:
            from gui.mesh_dialog import MeshDialog
            MeshDialog(self.parent)
        except ImportError as e:
            self.log(f"Ошибка: не удалось загрузить диалог конвертации: {e}")
            messagebox.showerror("Ошибка", "Модуль mesh_dialog не найден. Проверьте файл gui/mesh_dialog.py")

    def stop_reconstruction(self):
        """Остановка процесса"""
        if self.colmap_runner:
            self.colmap_runner.stop()
            self.log("Процесс остановлен пользователем")

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