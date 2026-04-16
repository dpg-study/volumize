import tkinter as tk
from tkinter import ttk, filedialog
import open3d as o3d
import numpy as np
import threading
import os
import time
import queue


class Real3DViewer:
    def __init__(self, parent_frame, config, embedded=False):
        self.parent = parent_frame
        self.config = config
        self.embedded = embedded
        self.vis = None
        self.geometry = None
        self.coord_frame = None
        self.show_coord = True
        self.is_loaded = False
        self.view_control = None
        self.is_running = True
        self.task_queue = queue.Queue()

        self.setup_ui()
        self.start_viewer_thread()

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        control_panel = ttk.Frame(self.main_frame)
        control_panel.pack(fill=tk.X, pady=5)

        ttk.Button(control_panel, text="Загрузить модель",
                   command=self.load_model_dialog).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="Сбросить вид",
                   command=self.reset_view).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="Очистить",
                   command=self.clear_viewer).pack(side=tk.LEFT, padx=2)

        self.toggle_coord_btn = ttk.Button(control_panel, text="Скрыть стрелки",
                                           command=self.toggle_coord_frame)
        self.toggle_coord_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="Облако точек",
                   command=self.show_pointcloud).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="Поверхность",
                   command=self.create_mesh).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="Скриншот",
                   command=self.take_screenshot).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="Готов к работе")
        status_label = ttk.Label(control_panel, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=10)

        info_frame = ttk.LabelFrame(self.main_frame, text="Управление")
        info_frame.pack(fill=tk.X, pady=5)

        info_text = """Мышь: Левая кнопка - вращение | Правая - масштаб | Колесо - приближение
Клавиши: R - сброс вида | C - очистить | F - скрыть/показать стрелки | P - облако точек | M - поверхность | S - скриншот"""

        ttk.Label(info_frame, text=info_text, font=('Arial', 9)).pack(pady=5)

        self.viewer_frame = ttk.Frame(self.main_frame)
        self.viewer_frame.pack(fill=tk.BOTH, expand=True)

    def start_viewer_thread(self):
        def viewer_thread():
            self.vis = o3d.visualization.VisualizerWithKeyCallback()

            width, height = 800, 600
            if self.embedded:
                try:
                    self.parent.update()
                    width = max(400, self.parent.winfo_width())
                    height = max(300, self.parent.winfo_height())
                except:
                    pass

            self.vis.create_window(
                window_name="3D Viewer",
                width=width,
                height=height,
                visible=True
            )

            self.coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=1.0)
            self.vis.add_geometry(self.coord_frame)

            opt = self.vis.get_render_option()
            opt.background_color = np.array([0.15, 0.15, 0.15])
            opt.point_size = 2.0

            self.view_control = self.vis.get_view_control()
            self.setup_key_callbacks()

            while self.is_running:
                try:
                    while not self.task_queue.empty():
                        task = self.task_queue.get_nowait()
                        task()
                except:
                    pass

                self.vis.poll_events()
                self.vis.update_renderer()
                time.sleep(0.01)

            self.vis.destroy_window()

        thread = threading.Thread(target=viewer_thread, daemon=True)
        thread.start()

    def setup_key_callbacks(self):
        self.vis.register_key_callback(ord('R'), lambda v: self.reset_view() or False)
        self.vis.register_key_callback(ord('C'), lambda v: self.clear_viewer() or False)
        self.vis.register_key_callback(ord('F'), lambda v: self.toggle_coord_frame() or False)
        self.vis.register_key_callback(ord('P'), lambda v: self.show_pointcloud() or False)
        self.vis.register_key_callback(ord('M'), lambda v: self.create_mesh() or False)
        self.vis.register_key_callback(ord('S'), lambda v: self.take_screenshot() or False)

    def clear_viewer(self):
        def action():
            self.vis.clear_geometries()
            if self.show_coord and self.coord_frame:
                self.vis.add_geometry(self.coord_frame)
            self.geometry = None
            self.is_loaded = False
            self.status_var.set("Вьювер очищен")

        self.task_queue.put(action)

    def toggle_coord_frame(self):
        def action():
            self.show_coord = not self.show_coord
            if self.show_coord:
                self.vis.add_geometry(self.coord_frame, reset_bounding_box=False)
                self.toggle_coord_btn.config(text="Скрыть стрелки")
            else:
                self.vis.remove_geometry(self.coord_frame, reset_bounding_box=False)
                self.toggle_coord_btn.config(text="Показать стрелки")

        self.task_queue.put(action)

    def load_model_dialog(self):
        filename = filedialog.askopenfilename(
            filetypes=[("3D files", "*.ply *.obj *.stl"), ("All files", "*.*")]
        )
        if filename:
            self.load_model(filename)

    def load_model(self, filepath):
        self.status_var.set("Загрузка...")

        def worker():
            try:
                ext = os.path.splitext(filepath)[1].lower()
                if ext == '.ply':
                    try:
                        geom = o3d.io.read_triangle_mesh(filepath)
                        if not geom.has_triangles():
                            geom = o3d.io.read_point_cloud(filepath)
                    except:
                        geom = o3d.io.read_point_cloud(filepath)
                elif ext in ['.obj', '.stl']:
                    geom = o3d.io.read_triangle_mesh(filepath)
                else:
                    geom = o3d.io.read_point_cloud(filepath)

                geom.translate(-geom.get_center())

                def update_vis():
                    self.vis.clear_geometries()
                    if self.show_coord: self.vis.add_geometry(self.coord_frame)
                    self.vis.add_geometry(geom)
                    self.geometry = geom
                    self.reset_view()
                    self.is_loaded = True
                    self.status_var.set(f"Загружено: {os.path.basename(filepath)}")

                self.task_queue.put(update_vis)
            except Exception as e:
                self.status_var.set(f"Ошибка: {str(e)}")

        threading.Thread(target=worker, daemon=True).start()

    def reset_view(self):
        def action():
            if self.view_control:
                self.view_control.set_front([0, 0, -1])
                self.view_control.set_up([0, -1, 0])
                self.view_control.set_zoom(0.8)

        self.task_queue.put(action)

    def show_pointcloud(self):
        if not self.geometry: return

        def worker():
            if isinstance(self.geometry, o3d.geometry.TriangleMesh):
                pcd = self.geometry.sample_points_uniformly(number_of_points=50000)

                def update():
                    self.vis.clear_geometries()
                    if self.show_coord: self.vis.add_geometry(self.coord_frame)
                    self.vis.add_geometry(pcd)
                    self.geometry = pcd

                self.task_queue.put(update)

        threading.Thread(target=worker, daemon=True).start()

    def create_mesh(self):
        if not isinstance(self.geometry, o3d.geometry.PointCloud): return
        self.status_var.set("Обработка...")

        def worker():
            try:
                self.geometry.estimate_normals()
                mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(self.geometry, depth=9)

                def update():
                    self.vis.clear_geometries()
                    if self.show_coord: self.vis.add_geometry(self.coord_frame)
                    self.vis.add_geometry(mesh)
                    self.geometry = mesh
                    self.status_var.set("Сетка создана")

                self.task_queue.put(update)
            except Exception as e:
                self.status_var.set(f"Ошибка: {str(e)}")

        threading.Thread(target=worker, daemon=True).start()

    def take_screenshot(self):
        filename = filedialog.asksaveasfilename(defaultextension=".png")
        if filename:
            self.task_queue.put(lambda: self.vis.capture_screen_image(filename))

    def close(self):
        self.is_running = False