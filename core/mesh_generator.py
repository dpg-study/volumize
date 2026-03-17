import open3d as o3d
import numpy as np
import os
import time


class MeshGenerator:
    """Класс для преобразования облака точек в 3D-модель без дыр"""

    def __init__(self):
        self.pcd = None
        self.mesh = None
        self.debug = True

    def log(self, message):
        """Вывод отладочных сообщений"""
        if self.debug:
            print(f"🔵 {message}")

    def load_point_cloud(self, filepath):
        """Загружает облако точек из файла"""
        try:
            self.log(f"Загрузка файла: {filepath}")
            file_size = os.path.getsize(filepath) / (1024 * 1024)
            self.log(f"Размер файла: {file_size:.2f} МБ")

            self.pcd = o3d.io.read_point_cloud(filepath)

            if self.pcd is None:
                print("🔴 Ошибка: PCD is None")
                return False

            points_count = len(self.pcd.points)
            self.log(f"Загружено точек: {points_count}")

            if self.pcd.is_empty():
                print("🔴 Ошибка: Облако точек пустое")
                return False

            if self.pcd.has_normals():
                self.log("Облако уже имеет нормали")
            if self.pcd.has_colors():
                self.log("Облако имеет цвета")

            self.log("Успешно загружено")
            return True

        except Exception as e:
            print(f"🔴 Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_hole_free_mesh(self, depth=11, quality="high"):
        """
        Многоэтапный метод для создания модели без дыр
        """
        if self.pcd is None:
            print("🔴 Ошибка: облако точек не загружено")
            return None

        start_time = time.time()
        self.log("=" * 50)
        self.log(f"НАЧАЛО РЕКОНСТРУКЦИИ (качество: {quality}, глубина: {depth})")
        self.log(f"Исходных точек: {len(self.pcd.points)}")
        self.log("=" * 50)

        # Настройки качества
        if quality == "draft":
            normals_radius = 0.15
            normals_max_nn = 30
            orient_iter = 20
            poisson_depth = min(depth, 9)
            clean_threshold = 0.005
            voxel_divider = 30
            smooth_iterations = 0
        elif quality == "medium":
            normals_radius = 0.2
            normals_max_nn = 50
            orient_iter = 40
            poisson_depth = min(depth, 10)
            clean_threshold = 0.002
            voxel_divider = 40
            smooth_iterations = 1
        else:  # high
            normals_radius = 0.25
            normals_max_nn = 80
            orient_iter = 60
            poisson_depth = depth
            clean_threshold = 0.001
            voxel_divider = 60
            smooth_iterations = 2

        self.log(f"Параметры: радиус нормалей={normals_radius}, глубина Poisson={poisson_depth}")

        # Этап 1: Оценка нормалей
        self.log("Этап 1/7: Оценка нормалей...")
        if not self.pcd.has_normals():
            self.pcd.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(
                    radius=normals_radius,
                    max_nn=normals_max_nn
                )
            )
            self.log("✓ Нормали оценены")
        else:
            self.log("✓ Нормали уже есть")

        # Этап 2: Согласование нормалей
        self.log("Этап 2/7: Согласование нормалей...")
        try:
            self.pcd.orient_normals_consistent_tangent_plane(orient_iter)
            self.log("✓ Нормали согласованы")
        except:
            self.log("⚠ Согласование не удалось, продолжаем...")

        # Этап 3: Poisson реконструкция
        self.log(f"Этап 3/7: Poisson реконструкция...")

        try:
            mesh_dense, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                self.pcd,
                depth=poisson_depth,
                linear_fit=True,
                width=0.3
            )

            vertices_before = len(mesh_dense.vertices)
            triangles_before = len(mesh_dense.triangles)
            self.log(f"✓ Poisson завершен: {vertices_before} вершин, {triangles_before} треугольников")

            # Проверка на аномально маленький результат
            if vertices_before < 100000 and quality != "draft":
                self.log(f"⚠ Мало вершин! Пробуем depth={poisson_depth - 1}...")
                mesh_dense, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                    self.pcd,
                    depth=poisson_depth - 1,
                    linear_fit=True
                )
                vertices_before = len(mesh_dense.vertices)
                self.log(f"✓ Повторный Poisson: {vertices_before} вершин")

        except Exception as e:
            self.log(f"❌ Ошибка Poisson: {e}")
            return None

        # Этап 4: Мягкая очистка
        self.log("Этап 4/7: Мягкая очистка...")
        if len(densities) > 0 and len(densities) == len(mesh_dense.vertices):
            threshold = np.quantile(densities, clean_threshold)
            vertices_to_remove = densities < threshold
            mesh_dense.remove_vertices_by_mask(vertices_to_remove)

            vertices_after = len(mesh_dense.vertices)
            self.log(f"✓ Удалено {vertices_before - vertices_after} проблемных вершин")
        else:
            self.log("⚠ Пропускаем очистку (несоответствие размеров)")

        # Этап 5: Удаление летающих точек
        self.log("Этап 5/7: Удаление летающих объектов...")
        try:
            triangle_clusters, cluster_n_triangles, _ = mesh_dense.cluster_connected_triangles()

            if len(cluster_n_triangles) > 1:
                triangle_clusters = np.asarray(triangle_clusters)
                cluster_n_triangles = np.asarray(cluster_n_triangles)

                largest_idx = np.argmax(cluster_n_triangles)
                largest_size = cluster_n_triangles[largest_idx]

                mask = np.ones(len(triangle_clusters), dtype=bool)
                removed_count = 0

                for i, size in enumerate(cluster_n_triangles):
                    if i != largest_idx and size < largest_size * 0.01:
                        mask[triangle_clusters == i] = False
                        removed_count += size

                if removed_count > 0:
                    mesh_dense.remove_triangles_by_mask(~mask)
                    mesh_dense.remove_unreferenced_vertices()
                    self.log(f"✓ Удалено {removed_count} летающих треугольников")
                else:
                    self.log("✓ Летающих объектов не найдено")
            else:
                self.log("✓ Летающих объектов не найдено")

        except Exception as e:
            self.log(f"⚠ Не удалось удалить летающие точки: {e}")

        # Этап 6: Заполнение больших дыр (ИСПРАВЛЕНО для вашей версии)
        self.log("Этап 6/7: Заполнение дыр...")
        try:
            # Проверяем, есть ли дыры
            edges = mesh_dense.get_non_manifold_edges(allow_boundary_edges=True)
            if len(edges) == 0:
                self.log("✓ Дыр не обнаружено")
            else:
                self.log(f"Найдено {len(edges)} граничных ребер")

                # Вычисляем размер вокселя (для информации)
                bbox = mesh_dense.get_axis_aligned_bounding_box()
                bbox_size = bbox.get_max_bound() - bbox.get_min_bound()
                voxel_size = np.mean(bbox_size) / voxel_divider

                self.log(f"Размер вокселя: {voxel_size:.4f}")

                # Альтернативный метод: сглаживание + субдивизия
                self.log("Применяю сглаживание для закрытия дыр...")

                # Несколько проходов сглаживания
                for i in range(3):
                    mesh_dense = mesh_dense.filter_smooth_laplacian(2)

                # Субдивизия (уточнение сетки) - помогает закрыть мелкие дыры
                try:
                    mesh_dense = mesh_dense.subdivide_midpoint(number_of_iterations=1)
                    self.log("✓ Выполнена субдивизия сетки")
                except:
                    pass

                self.log("✓ Дыры частично закрыты")

        except Exception as e:
            self.log(f"⚠ Ошибка при заполнении дыр: {e}")

        # Этап 7: Финальное сглаживание
        if smooth_iterations > 0:
            self.log(f"Этап 7/7: Финальное сглаживание ({smooth_iterations} итераций)...")
            try:
                mesh_dense = mesh_dense.filter_smooth_laplacian(smooth_iterations)
                self.log("✓ Сглаживание выполнено")
            except Exception as e:
                self.log(f"⚠ Ошибка сглаживания: {e}")

        # Финальная очистка
        mesh_dense.remove_degenerate_triangles()
        mesh_dense.remove_duplicated_vertices()
        mesh_dense.remove_unreferenced_vertices()

        # Проверка на водонепроницаемость
        try:
            if mesh_dense.is_watertight():
                self.log("✓ Модель водонепроницаема (без дыр)")
            else:
                self.log("⚠ Модель имеет мелкие дыры")
        except:
            pass

        vertices_final = len(mesh_dense.vertices)
        triangles_final = len(mesh_dense.triangles)

        elapsed_time = time.time() - start_time
        self.log("=" * 50)
        self.log("РЕКОНСТРУКЦИЯ ЗАВЕРШЕНА")
        self.log(f"Время: {elapsed_time:.1f} секунд")
        self.log(f"Итоговая модель: {vertices_final} вершин, {triangles_final} треугольников")
        self.log("=" * 50)

        self.mesh = mesh_dense
        return self.mesh

    def generate_mesh_poisson(self, depth=11, remove_low_density=True):
        """Оригинальный метод Пуассона (для совместимости)"""
        if self.pcd is None:
            return None

        self.pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=0.1,
                max_nn=50
            )
        )

        self.pcd.orient_normals_consistent_tangent_plane(20)

        self.mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            self.pcd,
            depth=depth,
            linear_fit=True
        )

        if remove_low_density and len(densities) > 0:
            vertices_to_remove = densities < np.quantile(densities, 0.005)
            self.mesh.remove_vertices_by_mask(vertices_to_remove)

        return self.mesh

    def generate_mesh_alpha(self, alpha=0.03):
        """Создает mesh методом Alpha Shapes"""
        if self.pcd is None:
            return None
        self.mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(self.pcd, alpha)
        return self.mesh

    def generate_mesh_ball_pivoting(self, radii=None):
        """Создает mesh методом Ball Pivoting"""
        if self.pcd is None:
            return None
        self.pcd.estimate_normals()
        if radii is None:
            distances = self.pcd.compute_nearest_neighbor_distance()
            avg_dist = np.mean(distances)
            radii = [avg_dist * 1.5, avg_dist * 3, avg_dist * 5]
        self.mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
            self.pcd, o3d.utility.DoubleVector(radii)
        )
        return self.mesh

    def simplify_mesh(self, target_triangles=50000):
        """Упрощает mesh"""
        if self.mesh is None:
            return None
        self.mesh = self.mesh.simplify_quadric_decimation(target_triangles)
        return self.mesh

    def smooth_mesh(self, iterations=5):
        """Сглаживает mesh"""
        if self.mesh is None:
            return None
        self.mesh = self.mesh.filter_smooth_laplacian(iterations)
        return self.mesh

    def clean_mesh(self):
        """Очищает mesh от артефактов"""
        if self.mesh is None:
            return None

        try:
            self.mesh.remove_degenerate_triangles()
            self.mesh.remove_duplicated_vertices()
            self.mesh.remove_duplicated_triangles()
            self.mesh.remove_unreferenced_vertices()
        except Exception as e:
            print(f"Ошибка при очистке mesh: {e}")

        return self.mesh

    def save_mesh(self, filepath):
        """Сохраняет mesh в файл"""
        if self.mesh is None:
            return False
        return o3d.io.write_triangle_mesh(filepath, self.mesh)

    def get_info(self):
        """Возвращает информацию о модели"""
        info = {}
        if self.pcd:
            info['points'] = len(self.pcd.points)
        if self.mesh:
            info['vertices'] = len(self.mesh.vertices)
            info['triangles'] = len(self.mesh.triangles)
            try:
                info['watertight'] = self.mesh.is_watertight()
            except:
                info['watertight'] = False
        return info