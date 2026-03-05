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
        control_panel.pack(fill=tk.X, pady=5)

        ttk.Button(control_panel, text="⟲ Сбросить вид",
                   command=self.reset_view).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="🔍 Приблизить",
                   command=lambda: self.zoom(0.8)).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="🔍 Отдалить",
                   command=lambda: self.zoom(1.2)).pack(side=tk.LEFT, padx=2)

        self.loading_label = ttk.Label(control_panel, text="")
        self.loading_label.pack(side=tk.RIGHT, padx=10)

    def show_start_message(self):
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas.winfo_width() // 2 if self.canvas.winfo_width() > 1 else 200,
            self.canvas.winfo_height() // 2 if self.canvas.winfo_height() > 1 else 150,
            text="Загрузите 3D модель для просмотра",
            fill="white",
            font=("Arial", 14)
        )

    def load_model(self, ply_file_path):
        if self.is_loading:
            return

        self.is_loading = True
        self.loading_label.config(text="⏳ Загрузка...")

        thread = threading.Thread(target=self._load_model_thread,
                                  args=(ply_file_path,))
        thread.daemon = True
        thread.start()

    def _load_model_thread(self, ply_file_path):
        try:
            plydata = PlyData.read(ply_file_path)
            vertices = plydata['vertex']

            x = vertices['x']
            y = vertices['y']
            z = vertices['z']

            self.canvas_frame.after(0, self._update_canvas, (x, y, z))

        except Exception as e:
            self.canvas_frame.after(0, self.show_error, str(e))
        finally:
            self.is_loading = False

    def _update_canvas(self, points):
        x, y, z = points

        x = np.array(x)
        y = np.array(y)
        z = np.array(z)

        x = x - x.mean()
        y = y - y.mean()
        z = z - z.mean()

        max_val = max(np.abs(x).max(), np.abs(y).max(), np.abs(z).max())
        if max_val > 0:
            x = x / max_val * 200
            y = y / max_val * 200
            z = z / max_val * 200

        width = self.canvas.winfo_width() or 600
        height = self.canvas.winfo_height() or 400
        center_x, center_y = width // 2, height // 2

        self.canvas.delete("all")

        for i in range(0, len(x), max(1, len(x) // 1000)):
            screen_x = center_x + x[i]
            screen_y = center_y - y[i]

            size = 2 + z[i] / 50

            z_norm = (z[i] + 200) / 400
            r = int(min(255, max(0, z_norm * 255)))
            b = int(min(255, max(0, (1 - z_norm) * 255)))
            color = f'#{r:02x}00{b:02x}'

            self.canvas.create_oval(
                screen_x - size, screen_y - size,
                screen_x + size, screen_y + size,
                fill=color, outline=""
            )

        self.loading_label.config(text=f"✅ {len(x)} точек")

    def show_error(self, error_msg):
        self.loading_label.config(text="❌ Ошибка")
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
            text=f"Ошибка: {error_msg[:50]}",
            fill="red",
            font=("Arial", 12)
        )

    def reset_view(self):
        pass

    def zoom(self, factor):
        pass