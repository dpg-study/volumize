import tkinter as tk
from tkinter import ttk
import numpy as np
from plyfile import PlyData
import threading
from tiny_3d_engine.scene3d import Scene3D
from tiny_3d_engine.engine import Engine3D


class ModelViewer3D:
    def __init__(self, parent_frame, config):
        self.parent = parent_frame
        self.config = config
        self.scene = None
        self.engine = None
        self.current_model = None
        self.is_loading = False
        self.canvas = None
        self.frame = ttk.Frame(parent_frame)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.setup_controls()
        self.canvas_frame = ttk.Frame(self.frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.show_start_message()

    def setup_controls(self):
        control_panel = ttk.Frame(self.frame)
        control_panel.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        self.loading_label = ttk.Label(control_panel, text="Модель не загружена")
        self.loading_label.pack(side=tk.LEFT)

    def show_start_message(self):
        self.canvas.create_text(
            400, 300,
            text="Здесь будет отображена 3D модель после реконструкции",
            fill="white", font=("Arial", 12)
        )

    def load_model(self, ply_path):
        if self.is_loading: return
        self.is_loading = True
        self.loading_label.config(text="Загрузка...")
        thread = threading.Thread(target=self._load_thread, args=(ply_path,))
        thread.daemon = True
        thread.start()

    def _load_thread(self, ply_path):
        try:
            plydata = PlyData.read(ply_path)
            x = plydata['vertex']['x']
            y = plydata['vertex']['y']
            z = plydata['vertex']['z']
            self.parent.after(0, lambda: self.draw_points(x, y, z))
        except Exception as e:
            self.parent.after(0, lambda: self.show_error(str(e)))
        finally:
            self.is_loading = False

    def draw_points(self, x, y, z):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        center_x, center_y = w // 2, h // 2

        for i in range(0, len(x), max(1, len(x) // 1000)):
            screen_x = center_x + x[i]
            screen_y = center_y - y[i]
            size = 2
            z_norm = (z[i] + 200) / 400
            r = int(min(255, max(0, z_norm * 255)))
            b = int(min(255, max(0, (1 - z_norm) * 255)))
            color = f'#{r:02x}00{b:02x}'
            self.canvas.create_oval(
                screen_x - size, screen_y - size,
                screen_x + size, screen_y + size,
                fill=color, outline=""
            )
        self.loading_label.config(text=f"Загружено: {len(x)} точек")

    def show_error(self, error_msg):
        self.loading_label.config(text="Ошибка загрузки")