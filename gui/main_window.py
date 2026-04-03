import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import sys

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

        setup_styles()
        self.parent.configure(bg='#1B1E23')
        self.pack(fill=tk.BOTH, expand=True)

        self.setup_ui()
        self.check_colmap()

    def setup_ui(self):
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(paned, width=350)
        paned.add(left_panel, weight=0)

        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=3)

        self.create_control_panel(left_panel)
        self.viewer = Real3DViewer(right_panel, self.config, embedded=True)
        self.create_status_bar(main_container)

    def create_control_panel(self, parent):
        container = ttk.Frame(parent, padding=(0, 0, 15, 0))
        container.pack(fill=tk.BOTH, expand=True)

        proj_card = ttk.LabelFrame(container, text=" ПРОЕКТ ", padding=15)
        proj_card.pack(fill=tk.X, pady=(0, 15))

        self.folder_var = tk.StringVar(value="Папка не выбрана")
        ttk.Entry(proj_card, textvariable=self.folder_var, state='readonly').pack(fill=tk.X, pady=(0, 8))
        ttk.Button(proj_card, text="ВЫБРАТЬ ИЗОБРАЖЕНИЯ", command=self.select_folder).pack(fill=tk.X)

        self.status_label = ttk.Label(proj_card, text="Ожидание данных...", foreground='#5C6370', font=('Inter', 9))
        self.status_label.pack(anchor=tk.W, pady=(8, 0))

        act_card = ttk.LabelFrame(container, text=" УПРАВЛЕНИЕ ", padding=15)
        act_card.pack(fill=tk.X, pady=15)

        self.start_btn = ttk.Button(act_card, text="СТАРТ РЕКОНСТРУКЦИИ", style='Accent.TButton',
                                    state='disabled', command=self.start_reconstruction)
        self.start_btn.pack(fill=tk.X, pady=(0, 5))

        self.stop_btn = ttk.Button(act_card, text="ОСТАНОВИТЬ", style='Stop.TButton',
                                   state='disabled', command=self.stop_reconstruction)
        self.stop_btn.pack(fill=tk.X, pady=5)

        ttk.Separator(act_card).pack(fill=tk.X, pady=10)

        ttk.Button(act_card, text="ГЕНЕРИРОВАТЬ MESH", command=self.open_mesh_dialog).pack(fill=tk.X)
        ttk.Button(act_card, text="ЗАГРУЗИТЬ PLY", command=lambda: self.viewer.load_model_dialog()).pack(fill=tk.X,
                                                                                                         pady=5)

    def create_status_bar(self, parent):
        self.progress = ttk.Progressbar(parent, mode='indeterminate', style='Custom.Horizontal.TProgressbar')
        self.progress.pack(fill=tk.X, pady=(15, 5))

        self.log_text = tk.Text(parent, height=6, bg='#181A1F', fg='#ABB2BF', font=('Consolas', 9),
                                borderwidth=0, padx=10, pady=10, insertbackground='white')
        self.log_text.pack(fill=tk.X)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            self.current_project_dir = folder
            self.check_photos(folder)

    def check_photos(self, folder):
        exts = ('.jpg', '.jpeg', '.png')
        try:
            photos = [f for f in os.listdir(folder) if f.lower().endswith(exts)]
            count = len(photos)
            if count >= self.config.MIN_PHOTOS:
                self.status_label.config(text=f"✓ Найдено фото: {count}", foreground='#98C379')
                self.start_btn.config(state='normal')
            else:
                self.status_label.config(text=f"⚠ Нужно минимум {self.config.MIN_PHOTOS} фото (найдено {count})",
                                         foreground='#E06C75')
                self.start_btn.config(state='disabled')
        except Exception as e:
            self.log(f"Ошибка при чтении папки: {e}")

    def log(self, message):
        self.log_text.insert(tk.END, f">> {message}\n")
        self.log_text.see(tk.END)
        self.parent.update_idletasks()

    def check_colmap(self):
        if self.config.get_colmap_path():
            self.log("COLMAP найден и готов.")
        else:
            self.log("ОШИБКА: COLMAP не найден.")

    def open_mesh_dialog(self):
        try:
            from gui.mesh_dialog import MeshDialog
            dialog = MeshDialog(self.parent)
        except ImportError as e:
            self.log(f"Ошибка импорта: {e}")
            messagebox.showerror("Ошибка",
                                 f"Не удалось загрузить модуль MeshDialog.\nПроверьте наличие файла gui/mesh_dialog.py\n{e}")
        except Exception as e:
            self.log(f"Непредвиденная ошибка: {e}")

    def start_reconstruction(self):
        if not self.current_project_dir:
            return

        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.progress.start(10)

        output_path = os.path.join(self.current_project_dir, "reconstruction_results")
        os.makedirs(output_path, exist_ok=True)

        thread = threading.Thread(
            target=self.colmap_runner.run_full_pipeline,
            args=(self.current_project_dir, output_path, lambda msg, p=None: self.log(msg)),
            daemon=True
        )
        thread.start()

    def stop_reconstruction(self):
        if self.colmap_runner:
            self.colmap_runner.stop()
        self.progress.stop()
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.log("Процесс остановлен.")