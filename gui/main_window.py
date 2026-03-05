import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from PIL import Image, ImageTk

from core.colmap_runner import COLMAPRunner
from gui.viewer_3d import ModelViewer3D
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

        self.create_top_panel()

        self.create_tabs()

        self.create_progress_bar()

    def create_top_panel(self):
        top_frame = ttk.LabelFrame(self, text="Настройки", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(top_frame, text="Папка с фотографиями:").grid(row=0, column=0, sticky=tk.W, pady=5)

        self.folder_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.folder_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(top_frame, text="Обзор...", command=self.select_folder).grid(row=0, column=2)

        self.photos_count_label = ttk.Label(top_frame, text="Нет фото")
        self.photos_count_label.grid(row=1, column=1, sticky=tk.W, pady=5)

        button_frame = ttk.Frame(top_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)

        self.start_btn = ttk.Button(button_frame, text="▶ Запустить реконструкцию",
                                    command=self.start_reconstruction, state='disabled')
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="⏹ Остановить",
                                   command=self.stop_reconstruction, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.view_btn = ttk.Button(button_frame, text="👁 Показать модель",
                                   command=self.show_model, state='disabled')
        self.view_btn.pack(side=tk.LEFT, padx=5)

    def create_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        viewer_tab = ttk.Frame(self.notebook)
        self.notebook.add(viewer_tab, text="🖥 3D Просмотр")

        self.viewer = ModelViewer3D(viewer_tab, self.config)

        log_tab = ttk.Frame(self.notebook)
        self.notebook.add(log_tab, text="📋 Лог выполнения")

        self.log_text = tk.Text(log_tab, wrap=tk.WORD, bg='#1e1e1e', fg='#d4d4d4')
        scrollbar = ttk.Scrollbar(log_tab, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_progress_bar(self):
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack(side=tk.RIGHT, padx=5)

    def check_colmap(self):
        colmap_path = self.config.get_colmap_path()
        if colmap_path:
            self.log(f"✅ COLMAP найден: {colmap_path}")
        else:
            self.log("❌ COLMAP не найден! Укажите путь в настройках.")
            messagebox.showwarning("Предупреждение",
                                   "COLMAP не найден. Реконструкция невозможна.")

    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с фотографиями")
        if folder:
            self.folder_var.set(folder)
            self.check_photos(folder)

    def check_photos(self, folder):
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

        if photos:
            self.log(f"📸 Примеры: {', '.join(photos[:5])}")

    def start_reconstruction(self):
        folder = self.folder_var.get()

        if not folder or not os.path.exists(folder):
            self.log("❌ Ошибка: папка с фото не существует")
            return

        folder = os.path.normpath(folder)

        project_name = os.path.basename(folder)
        self.current_project_dir = os.path.join(
            os.path.dirname(folder),
            f"{project_name}_3d_model"
        )
        self.current_project_dir = os.path.normpath(self.current_project_dir)

        try:
            os.makedirs(self.current_project_dir, exist_ok=True)
            self.log(f"📁 Создана папка для результатов: {self.current_project_dir}")
        except Exception as e:
            self.log(f"❌ Ошибка создания папки: {e}")
            return

        colmap_path = self.config.get_colmap_path()
        if not colmap_path:
            self.log("❌ COLMAP не найден! Реконструкция невозможна.")
            messagebox.showerror("Ошибка", "COLMAP не найден! Проверьте настройки.")
            return

        self.log(f"✅ COLMAP найден: {colmap_path}")
        self.log(f"📁 Фото (нормализовано): {folder}")
        self.log(f"📁 Результат: {self.current_project_dir}")

        valid_extensions = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
        photos = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        if len(photos) < self.config.MIN_PHOTOS:
            self.log(f"❌ Слишком мало фото: {len(photos)}. Нужно минимум {self.config.MIN_PHOTOS}")
            messagebox.showerror("Ошибка", f"Слишком мало фото: {len(photos)}\nНужно минимум {self.config.MIN_PHOTOS}")
            return

        self.log(f"📸 Найдено фото: {len(photos)}")
        self.log(f"📸 Примеры: {', '.join(photos[:5])}")

        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.view_btn.config(state='disabled')
        self.progress.start()
        self.progress_label.config(text="Реконструкция...")

        self.log("=" * 50)
        self.log("🚀 НАЧАЛО РЕКОНСТРУКЦИИ")
        self.log("=" * 50)

        def run_thread():
            try:
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
                        possible_ply = os.path.join(self.current_project_dir, "fused.ply")
                        if os.path.exists(possible_ply):
                            self.parent.after(0, self.reconstruction_complete, possible_ply)
                        else:
                            self.parent.after(0, self.reconstruction_failed, "PLY файл не найден")
                else:
                    self.parent.after(0, self.reconstruction_failed, "Ошибка в процессе реконструкции")

            except Exception as e:
                self.parent.after(0, self.reconstruction_failed, str(e))

        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()

    def _run_colmap_thread(self, image_dir, output_dir):
        def log_callback(msg, progress=None):
            self.parent.after(0, self.log, msg)
            if progress is not None:
                self.parent.after(0, self.update_progress, progress)

        success = self.colmap_runner.run_full_pipeline(image_dir, output_dir, log_callback)

        if success:
            ply_file = os.path.join(output_dir, "dense", "fused.ply")
            if os.path.exists(ply_file):
                self.parent.after(0, self.reconstruction_complete, ply_file)
            else:
                self.parent.after(0, self.reconstruction_failed, "PLY файл не найден")
        else:
            self.parent.after(0, self.reconstruction_failed, "Ошибка в процессе реконструкции")

    def reconstruction_complete(self, ply_file):
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

            if messagebox.askyesno("Готово",
                                   f"Реконструкция завершена!\nРазмер модели: {file_size:.2f} МБ\nПоказать 3D-модель?"):
                self.show_model(ply_file)
        else:
            self.log(f"❌ Файл модели не найден: {ply_file}")

    def reconstruction_failed(self, error_msg):
        self.progress.stop()
        self.progress_label.config(text="Ошибка")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        self.log(f"❌ ОШИБКА: {error_msg}")
        messagebox.showerror("Ошибка", f"Реконструкция не удалась:\n{error_msg}")

    def show_model(self, ply_file=None):
        if ply_file is None:
            ply_file = filedialog.askopenfilename(
                title="Выберите PLY файл",
                filetypes=[("PLY files", "*.ply")]
            )
            if not ply_file:
                return

        self.notebook.select(0)

        self.viewer.load_model(ply_file)
        self.log(f"👁 Загружена модель: {ply_file}")

    def stop_reconstruction(self):
        if self.colmap_runner:
            self.colmap_runner.stop()
            self.log("⛔ Процесс остановлен пользователем")

        self.progress.stop()
        self.progress_label.config(text="Остановлено")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def update_progress(self, value):
        self.progress_label.config(text=f"Выполнено: {value}%")

    def log(self, message):
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.parent.update_idletasks()