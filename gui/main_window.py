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
        top_frame = ttk.LabelFrame(self, text="Настройки", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        path_frame = ttk.Frame(top_frame)
        path_frame.pack(fill=tk.X)
        ttk.Label(path_frame, text="Папка с фото:").pack(side=tk.LEFT)
        self.path_entry = ttk.Entry(path_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(path_frame, text="Обзор", command=self.browse_folder).pack(side=tk.LEFT)

        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="Запустить реконструкцию", command=self.start_reconstruction)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Остановить", command=self.stop_reconstruction, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Открыть результат", command=self.show_model).pack(side=tk.LEFT, padx=5)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.viewer = ModelViewer3D(self.notebook, self.config)
        self.notebook.add(self.viewer.frame, text="3D Вид")
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Лог процесса")
        self.log_text = tk.Text(log_frame, height=10, bg="#1e1e1e", fg="#d4d4d4")
        self.log_text.pack(fill=tk.BOTH, expand=True)

        progress_frame = ttk.Frame(self, padding=5)
        progress_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.progress_label = ttk.Label(progress_frame, text="Готов")
        self.progress_label.pack(side=tk.TOP, anchor=tk.W)
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X)

    def check_colmap(self):
        if not self.config.get_colmap_path():
            messagebox.showwarning("Предупреждение", "COLMAP не найден")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)

    def log(self, message):
        self.log_text.insert(tk.END, f"[{os.getpid()}] {message}\n")
        self.log_text.see(tk.END)

    def start_reconstruction(self):
        img_dir = self.path_entry.get()
        if not os.path.exists(img_dir):
            messagebox.showerror("Ошибка", "Путь не существует")
            return

        self.current_project_dir = os.path.join(os.path.dirname(img_dir), "reconstruction_result")
        os.makedirs(self.current_project_dir, exist_ok=True)

        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.notebook.select(1)

        thread = threading.Thread(target=self.run_thread, args=(img_dir, self.current_project_dir))
        thread.daemon = True
        thread.start()

    def run_thread(self, img_dir, out_dir):
        success = self.colmap_runner.run_full_pipeline(img_dir, out_dir, self.on_pipeline_event)
        if success:
            self.parent.after(0, lambda: self.finish_reconstruction(out_dir))
        else:
            self.parent.after(0, self.error_reconstruction)

    def on_pipeline_event(self, message, progress_val):
        if progress_val is not None:
            self.parent.after(0, lambda: self.update_progress(progress_val))
        self.parent.after(0, lambda: self.log(message))

    def finish_reconstruction(self, out_dir):
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        ply_file = os.path.join(out_dir, "result.ply")
        if os.path.exists(ply_file):
            self.show_model(ply_file)
        messagebox.showinfo("Готово", "Реконструкция завершена")

    def error_reconstruction(self):
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        messagebox.showerror("Ошибка", "Реконструкция не удалась")

    def show_model(self, ply_file=None):
        if ply_file is None:
            ply_file = filedialog.askopenfilename(filetypes=[("PLY files", "*.ply")])
            if not ply_file: return
        self.notebook.select(0)
        self.viewer.load_model(ply_file)

    def stop_reconstruction(self):
        if self.colmap_runner:
            self.colmap_runner.stop()
        self.progress_label.config(text="Остановлено")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def update_progress(self, value):
        self.progress['value'] = value
        self.progress_label.config(text=f"Выполнено: {int(value)}%")