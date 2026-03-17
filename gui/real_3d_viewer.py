import tkinter as tk
from tkinter import ttk, filedialog
import open3d as o3d
import numpy as np
import threading
import os
import time


class Real3DViewer:
    """Настоящий 3D-вьювер на базе Open3D с управлением"""

    def __init__(self, parent_frame, config):
        self.parent = parent_frame
        self.config = config
        self.vis = None
        self.geometry = None
        self.is_loaded = False
        self.view_control = None
        self.is_running = True

        # Создаем фрейм для управления
        self.setup_ui()

        # Запускаем вьювер в отдельном потоке
        self.start_viewer_thread()

    def setup_ui(self):
        """Создает панель управления"""
        # Главный фрейм
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Панель управления сверху
        control_panel = ttk.Frame(self.main_frame)
        control_panel.pack(fill=tk.X, pady=5)

        # Кнопки управления
        ttk.Button(control_panel, text="📂 Загрузить модель",
                   command=self.load_model_dialog).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="🔄 Сбросить вид",
                   command=self.reset_view).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="🎭 Облако точек",
                   command=self.show_pointcloud).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="🔷 Поверхность (Poisson)",
                   command=self.create_mesh).pack(side=tk.LEFT, padx=2)

        ttk.Button(control_panel, text="📸 Скриншот",
                   command=self.take_screenshot).pack(side=tk.LEFT, padx=2)

        # Статус
        self.status_var = tk.StringVar(value="Готов к работе")
        status_label = ttk.Label(control_panel, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=10)

        # Инструкция
        info_frame = ttk.LabelFrame(self.main_frame, text="Управление")
        info_frame.pack(fill=tk.X, pady=5)

        info_text = """🖱️ Мышь: Левая кнопка - вращение | Правая - масштаб | Колесо - приближение
⌨️ Клавиши: R - сброс вида | P - облако точек | M - поверхность | S - скриншот"""

        ttk.Label(info_frame, text=info_text, font=('Arial', 9)).pack(pady=5)

        # Фрейм для Open3D (будет вставлен позже)
        self.viewer_frame = ttk.Frame(self.main_frame)
        self.viewer_frame.pack(fill=tk.BOTH, expand=True)

    def start_viewer_thread(self):
        """Запускает Open3D в отдельном потоке"""

        def viewer_thread():
            # Создаем визуализатор
            self.vis = o3d.visualization.VisualizerWithKeyCallback()
            self.vis.create_window(
                window_name="3D Viewer",
                width=800,
                height=600,
                visible=True
            )

            # Добавляем координатную сетку
            coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=1.0)
            self.vis.add_geometry(coord_frame)

            # Настраиваем опции рендеринга
            opt = self.vis.get_render_option()
            opt.background_color = np.array([0.1, 0.1, 0.1])  # темно-серый
            opt.point_size = 2.0
            opt.line_width = 1.0

            # Получаем control для управления камерой
            self.view_control = self.vis.get_view_control()

            # Добавляем обработчики клавиш
            self.setup_key_callbacks()

            # Основной цикл
            while self.is_running:
                self.vis.poll_events()
                self.vis.update_renderer()
                time.sleep(0.01)

            self.vis.destroy_window()

        thread = threading.Thread(target=viewer_thread, daemon=True)
        thread.start()

    def setup_key_callbacks(self):
        """Настройка горячих клавиш"""
        if not self.vis:
            return

        # Сброс вида по клавише R
        def reset_callback(vis):
            self.reset_view()
            return False

        # Облако точек по клавише P
        def pointcloud_callback(vis):
            self.show_pointcloud()
            return False

        # Поверхность по клавише M
        def mesh_callback(vis):
            self.create_mesh()
            return False

        # Скриншот по клавише S
        def screenshot_callback(vis):
            self.take_screenshot()
            return False

        self.vis.register_key_callback(ord('R'), reset_callback)
        self.vis.register_key_callback(ord('P'), pointcloud_callback)
        self.vis.register_key_callback(ord('M'), mesh_callback)
        self.vis.register_key_callback(ord('S'), screenshot_callback)

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
        self.status_var.set(f"⏳ Загрузка: {os.path.basename(filepath)}...")

        def load_thread():
            try:
                # Определяем тип файла и загружаем
                if filepath.endswith('.ply'):
                    # Пробуем загрузить как mesh, если не получится - как pointcloud
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

                # Центрируем модель
                if self.geometry:
                    self.geometry.translate(-self.geometry.get_center())

                    # Добавляем в визуализатор
                    self.vis.add_geometry(self.geometry)

                    # Настраиваем камеру
                    self.view_control.set_front([0, 0, -1])
                    self.view_control.set_up([0, -1, 0])
                    self.view_control.set_zoom(1.0)

                    self.is_loaded = True
                    self.status_var.set(f"✅ Загружено: {os.path.basename(filepath)}")

            except Exception as e:
                self.status_var.set(f"❌ Ошибка: {str(e)}")

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
            # Если это mesh, конвертируем в облако точек
            if isinstance(self.geometry, o3d.geometry.TriangleMesh):
                pcd = self.geometry.sample_points_uniformly(number_of_points=100000)
                self.vis.clear_geometries()
                self.vis.add_geometry(pcd)
                self.geometry = pcd
                self.status_var.set("Режим: облако точек")

    def create_mesh(self):
        """Создает поверхность из облака точек методом Пуассона"""
        if isinstance(self.geometry, o3d.geometry.PointCloud):
            self.status_var.set("⏳ Построение поверхности...")

            def mesh_thread():
                try:
                    # Оцениваем нормали
                    self.geometry.estimate_normals(
                        search_param=o3d.geometry.KDTreeSearchParamHybrid(
                            radius=0.1, max_nn=30
                        )
                    )

                    # Строим поверхность
                    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                        self.geometry, depth=9
                    )

                    # Обрезаем низкокачественные области
                    vertices_to_remove = densities < np.quantile(densities, 0.1)
                    mesh.remove_vertices_by_mask(vertices_to_remove)

                    # Обновляем в визуализаторе
                    self.vis.clear_geometries()
                    self.vis.add_geometry(mesh)
                    self.geometry = mesh

                    self.status_var.set("✅ Поверхность построена")

                except Exception as e:
                    self.status_var.set(f"❌ Ошибка: {str(e)}")

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
                self.status_var.set(f"📸 Скриншот сохранен: {os.path.basename(filename)}")

    def close(self):
        """Закрывает вьювер"""
        self.is_running = False
        time.sleep(0.1)