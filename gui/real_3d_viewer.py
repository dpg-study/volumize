import tkinter as tk
from tkinter import ttk, filedialog
import open3d as o3d
import numpy as np
import threading
import os
import time


class Real3DViewer:
    """3D-вьювер на базе Open3D с управлением"""

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

        self.setup_ui()
        self.start_viewer_thread()

    def setup_ui(self):
        """Создает панель управления"""
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
        """Запускает Open3D в отдельном потоке"""

        def viewer_thread():
            self.vis = o3d.visualization.VisualizerWithKeyCallback()

            if self.embedded:
                try:
                    x = self.parent.winfo_rootx()
                    y = self.parent.winfo_rooty()
                    width = max(400, self.parent.winfo_width())
                    height = max(300, self.parent.winfo_height())
                except:
                    x, y, width, height = 100, 100, 800, 600
            else:
                x, y, width, height = 100, 100, 800, 600

            self.vis.create_window(
                window_name="3D Viewer",
                width=width,
                height=height,
                left=x,
                top=y,
                visible=True
            )

            self.coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=1.0)
            self.vis.add_geometry(self.coord_frame)

            opt = self.vis.get_render_option()
            opt.background_color = np.array([0.15, 0.15, 0.15])
            opt.point_size = 2.0
            opt.line_width = 1.0

            self.view_control = self.vis.get_view_control()
            self.setup_key_callbacks()

            while self.is_running:
                self.vis.poll_events()
                self.vis.update_renderer()

                if self.embedded:
                    time.sleep(0.05)
                else:
                    time.sleep(0.01)

            self.vis.destroy_window()

        thread = threading.Thread(target=viewer_thread, daemon=True)
        thread.start()
        time.sleep(1)

    def setup_key_callbacks(self):
        """Настройка горячих клавиш"""
        if not self.vis:
            return

        def reset_callback(vis):
            self.reset_view()
            return False

        def clear_callback(vis):
            self.clear_viewer()
            return False

        def toggle_coord_callback(vis):
            self.toggle_coord_frame()
            return False

        def pointcloud_callback(vis):
            self.show_pointcloud()
            return False

        def mesh_callback(vis):
            self.create_mesh()
            return False

        def screenshot_callback(vis):
            self.take_screenshot()
            return False

        self.vis.register_key_callback(ord('R'), reset_callback)
        self.vis.register_key_callback(ord('C'), clear_callback)
        self.vis.register_key_callback(ord('F'), toggle_coord_callback)
        self.vis.register_key_callback(ord('P'), pointcloud_callback)
        self.vis.register_key_callback(ord('M'), mesh_callback)
        self.vis.register_key_callback(ord('S'), screenshot_callback)

    def clear_viewer(self):
        """Очищает вьювер от всех моделей"""
        if not self.vis:
            return

        def clear_thread():
            self.vis.clear_geometries()
            if self.show_coord and self.coord_frame:
                self.vis.add_geometry(self.coord_frame)
            self.geometry = None
            self.is_loaded = False
            self.status_var.set("Вьювер очищен")

        thread = threading.Thread(target=clear_thread, daemon=True)
        thread.start()

    def toggle_coord_frame(self):
        """Показывает/скрывает координатные стрелки"""
        if not self.vis:
            return

        # ИСПРАВЛЕНО: убрал get_geometries()
        def toggle_thread():
            self.show_coord = not self.show_coord
            if self.show_coord:
                try:
                    self.vis.add_geometry(self.coord_frame, reset_bounding_box=False)
                except:
                    pass
                self.toggle_coord_btn.config(text="Скрыть стрелки")
                self.status_var.set("Стрелки показаны")
            else:
                try:
                    self.vis.remove_geometry(self.coord_frame, reset_bounding_box=False)
                except:
                    pass
                self.toggle_coord_btn.config(text="Показать стрелки")
                self.status_var.set("Стрелки скрыты")

        thread = threading.Thread(target=toggle_thread, daemon=True)
        thread.start()

    def load_model_dialog(self):
        """Диалог загрузки модели"""
        filename = filedialog.askopenfilename(
            title="Выберите 3D модель",
            filetypes=[
                ("PLY files", "*.ply"),
                ("OBJ files", "*.obj"),
                ("STL files", "*.stl"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.load_model(filename)

    def load_model(self, filepath):
        """Загружает модель из файла"""
        self.status_var.set(f"Загрузка: {os.path.basename(filepath)}...")

        def load_thread():
            try:
                if filepath.endswith('.ply'):
                    try:
                        mesh = o3d.io.read_triangle_mesh(filepath)
                        if mesh.has_triangles():
                            self.geometry = mesh
                        else:
                            self.geometry = o3d.io.read_point_cloud(filepath)
                    except:
                        self.geometry = o3d.io.read_point_cloud(filepath)

                elif filepath.endswith('.obj') or filepath.endswith('.stl'):
                    self.geometry = o3d.io.read_triangle_mesh(filepath)
                else:
                    self.geometry = o3d.io.read_point_cloud(filepath)

                if self.geometry:
                    self.geometry.translate(-self.geometry.get_center())

                    self.vis.clear_geometries()

                    if self.show_coord and self.coord_frame:
                        self.vis.add_geometry(self.coord_frame)

                    self.vis.add_geometry(self.geometry)

                    if self.view_control:
                        self.view_control.set_front([0, 0, -1])
                        self.view_control.set_up([0, -1, 0])
                        self.view_control.set_zoom(1.0)

                    self.is_loaded = True
                    self.status_var.set(f"Загружено: {os.path.basename(filepath)}")

            except Exception as e:
                self.status_var.set(f"Ошибка: {str(e)}")

        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()

    def reset_view(self):
        """Сброс вида камеры"""
        if self.view_control:
            self.view_control.set_front([0, 0, -1])
            self.view_control.set_up([0, -1, 0])
            self.view_control.set_zoom(1.0)
            self.status_var.set("Вид сброшен")

    def show_pointcloud(self):
        """Показывает как облако точек"""
        if self.geometry and self.vis:
            def convert_thread():
                if isinstance(self.geometry, o3d.geometry.TriangleMesh):
                    pcd = self.geometry.sample_points_uniformly(number_of_points=100000)

                    self.vis.clear_geometries()
                    if self.show_coord and self.coord_frame:
                        self.vis.add_geometry(self.coord_frame)
                    self.vis.add_geometry(pcd)
                    self.geometry = pcd
                    self.status_var.set("Режим: облако точек")

            thread = threading.Thread(target=convert_thread, daemon=True)
            thread.start()

    def create_mesh(self):
        """Создает поверхность из облака точек методом Пуассона"""
        if isinstance(self.geometry, o3d.geometry.PointCloud):
            self.status_var.set("Построение поверхности...")

            def mesh_thread():
                try:
                    self.geometry.estimate_normals(
                        search_param=o3d.geometry.KDTreeSearchParamHybrid(
                            radius=0.1, max_nn=30
                        )
                    )

                    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                        self.geometry, depth=9
                    )

                    vertices_to_remove = densities < np.quantile(densities, 0.1)
                    mesh.remove_vertices_by_mask(vertices_to_remove)

                    self.vis.clear_geometries()
                    if self.show_coord and self.coord_frame:
                        self.vis.add_geometry(self.coord_frame)
                    self.vis.add_geometry(mesh)
                    self.geometry = mesh

                    self.status_var.set("Поверхность построена")

                except Exception as e:
                    self.status_var.set(f"Ошибка: {str(e)}")

            thread = threading.Thread(target=mesh_thread, daemon=True)
            thread.start()

    def take_screenshot(self):
        """Делает скриншот текущего вида"""
        if self.vis:
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png")]
            )
            if filename:
                self.vis.capture_screen_image(filename)
                self.status_var.set(f"Скриншот сохранен: {os.path.basename(filename)}")

    def close(self):
        """Закрывает вьювер"""
        self.is_running = False
        time.sleep(0.1)