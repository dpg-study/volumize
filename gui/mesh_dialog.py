import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys

from core.mesh_generator import MeshGenerator


class MeshDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Настройки 3D Реконструкции (Mesh)")
        self.geometry("600x750")
        self.minsize(550, 700)
        self.configure(bg='#2b2b2b')

        self.mesh_gen = MeshGenerator()
        self.input_file = None

        self.transient(parent)
        self.grab_set()

        self.setup_ui()

    def setup_ui(self):
        scale_style = {
            "bg": "#2b2b2b",
            "fg": "white",
            "highlightthickness": 0,
            "orient": tk.HORIZONTAL,
            "troughcolor": "#404040",
            "activebackground": "#0078d4"
        }

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        file_group = ttk.LabelFrame(main_frame, text=" 1. ВХОДНЫЕ ДАННЫЕ ", padding=10)
        file_group.pack(fill=tk.X, pady=(0, 15))

        self.path_var = tk.StringVar(value="Выберите файл .ply")
        ttk.Entry(file_group, textvariable=self.path_var, state='readonly').pack(fill=tk.X, pady=(0, 5))
        ttk.Button(file_group, text="ОБЗОР ОБЛАКА ТОЧЕК", command=self.select_file).pack(fill=tk.X)

        gen_group = ttk.LabelFrame(main_frame, text=" 2. ПАРАМЕТРЫ ПОВЕРХНОСТИ (POISSON) ", padding=15)
        gen_group.pack(fill=tk.X, pady=10)

        ttk.Label(gen_group, text="Детализация (Depth 5-12):").pack(anchor=tk.W)
        self.depth_scale = tk.Scale(gen_group, from_=5, to=12, **scale_style)
        self.depth_scale.set(9)
        self.depth_scale.pack(fill=tk.X, pady=(0, 5))

        proc_group = ttk.LabelFrame(main_frame, text=" 3. СГЛАЖИВАНИЕ И ОПТИМИЗАЦИЯ ", padding=15)
        proc_group.pack(fill=tk.X, pady=10)

        ttk.Label(proc_group, text="Итерации сглаживания (Laplacian):").pack(anchor=tk.W)
        self.smooth_scale = tk.Scale(proc_group, from_=0, to=20, **scale_style)
        self.smooth_scale.set(5)
        self.smooth_scale.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(proc_group, text="Упрощение (целевое кол-во треугольников):").pack(anchor=tk.W)
        self.tri_scale = tk.Scale(proc_group, from_=10000, to=1000000, resolution=10000, **scale_style)
        self.tri_scale.set(100000)
        self.tri_scale.pack(fill=tk.X, pady=(0, 10))

        self.clean_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(proc_group, text="Автоматическая чистка (дубликаты, шум)", variable=self.clean_var).pack(
            anchor=tk.W)

        self.log_text = tk.Text(main_frame, height=6, bg='#1e1e1e', fg='#98C379', font=('Consolas', 9), borderwidth=0,
                                padx=10, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=15)

        self.run_btn = ttk.Button(main_frame, text="ЗАПУСТИТЬ ОБРАБОТКУ", style='Accent.TButton',
                                  state='disabled', command=self.start_processing)
        self.run_btn.pack(fill=tk.X)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Point Cloud", "*.ply")])
        if path:
            self.input_file = path
            self.path_var.set(os.path.basename(path))
            self.run_btn.config(state='normal')
            self.log(f"Выбран файл: {os.path.basename(path)}")

    def log(self, msg):
        self.log_text.insert(tk.END, f"> {msg}\n")
        self.log_text.see(tk.END)
        self.update_idletasks()

    def start_processing(self):
        self.run_btn.config(state='disabled')
        threading.Thread(target=self.process_logic, daemon=True).start()

    def process_logic(self):
        try:
            self.log("Загрузка облака точек...")
            if not self.mesh_gen.load_point_cloud(self.input_file):
                self.log("Ошибка загрузки.")
                return

            depth = self.depth_scale.get()
            self.log(f"Генерация поверхности (depth={depth})...")
            self.mesh_gen.generate_mesh_poisson(depth=depth)

            if self.clean_var.get():
                self.log("Очистка сетки от артефактов...")
                self.mesh_gen.clean_mesh()

            s_iters = self.smooth_scale.get()
            if s_iters > 0:
                self.log(f"Применение сглаживания ({s_iters} итераций)...")
                self.mesh_gen.smooth_mesh(iterations=s_iters)

            t_count = self.tri_scale.get()
            self.log(f"Упрощение геометрии до {t_count} полигонов...")
            self.mesh_gen.simplify_mesh(target_triangles=t_count)

            self.log("Обработка завершена. Выберите имя файла.")

            self.after(0, self.ask_save_name)

        except Exception as e:
            self.log(f"Ошибка: {str(e)}")
            self.run_btn.config(state='normal')

    def ask_save_name(self):
        default_name = os.path.basename(self.input_file).replace(".ply", "_mesh.ply")

        output_path = filedialog.asksaveasfilename(
            title="Сохранить 3D-модель",
            initialfile=default_name,
            defaultextension=".ply",
            filetypes=[("PLY mesh", "*.ply"), ("All files", "*.*")]
        )

        if output_path:
            if self.mesh_gen.save_mesh(output_path):
                self.log(f"Успешно сохранено: {os.path.basename(output_path)}")
                messagebox.showinfo("Успех", f"Модель успешно создана и сохранена:\n{output_path}")

                if hasattr(self.parent, 'main_window') and hasattr(self.parent.main_window, 'viewer'):
                    self.parent.main_window.viewer.load_model(output_path)
            else:
                self.log("Ошибка при сохранении файла.")
        else:
            self.log("Сохранение отменено.")

        self.run_btn.config(state='normal')