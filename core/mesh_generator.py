import open3d as o3d
import numpy as np
import os


class MeshGenerator:
    """Класс для преобразования облака точек в 3D-модель"""

    def __init__(self):
        self.pcd = None
        self.mesh = None

    def load_point_cloud(self, filepath):
        """Загружает облако точек из файла с отладкой"""
        try:
            print(f"🟡 Загрузка файла: {filepath}")
            print(f"🟡 Размер файла: {os.path.getsize(filepath) / (1024 * 1024):.2f} МБ")

            # Загружаем облако точек
            self.pcd = o3d.io.read_point_cloud(filepath)

            if self.pcd is None:
                print("🔴 PCD is None")
                return False

            points_count = len(self.pcd.points)
            print(f"🟡 Загружено точек: {points_count}")

            if self.pcd.is_empty():
                print("🔴 Облако точек пустое")
                return False

            print(f"🟢 Успешно загружено {points_count} точек")
            return True

        except Exception as e:
            print(f"🔴 Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_mesh_poisson(self, depth=11, remove_low_density=True):
        """
        Улучшенная версия метода Пуассона:
        - depth 11 вместо 9 (более детально)
        - Лучшая оценка нормалей (max_nn=50)
        - Больше итераций согласования (20)
        - linear_fit для лучшего сглаживания
        - Мягкая очистка (удаляем только 0.5% самых плохих областей)
        """
        if self.pcd is None:
            return None

        # Оцениваем нормали с лучшими параметрами
        self.pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=0.1,
                max_nn=50  # Увеличили с 30 до 50
            )
        )

        # Согласование нормалей для замкнутых объектов
        self.pcd.orient_normals_consistent_tangent_plane(20)  # Увеличили с 10 до 20

        # Строим поверхность методом Пуассона с linear_fit
        self.mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            self.pcd,
            depth=depth,  # 11 вместо 9
            linear_fit=True  # Добавили для лучшего сглаживания
        )

        # Очень мягкая очистка (удаляем только самые проблемные участки)
        if remove_low_density and len(densities) > 0:
            vertices_to_remove = densities < np.quantile(densities, 0.005)  # 0.5% вместо 1%
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
            radii = [avg_dist * 1.5, avg_dist * 3, avg_dist * 5]  # Добавили третий радиус
        self.mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
            self.pcd, o3d.utility.DoubleVector(radii)
        )
        return self.mesh

    def simplify_mesh(self, target_triangles=50000):
        """Упрощает mesh (уменьшает количество полигонов)"""
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

    def fill_small_holes(self, hole_size=0.5):
        """
        Заполняет небольшие дыры в модели.
        В Open3D нет прямого fill_holes, используем комбинацию методов.
        """
        if self.mesh is None:
            return None

        try:
            # 1. Сглаживаем края дыр
            self.mesh = self.mesh.filter_smooth_laplacian(3)

            # 2. Удаляем висячие вершины
            self.mesh.remove_unreferenced_vertices()

            # 3. Удаляем вырожденные треугольники
            self.mesh.remove_degenerate_triangles()

            # 4. Еще раз удаляем неиспользуемые вершины
            self.mesh.remove_unreferenced_vertices()

        except Exception as e:
            print(f"Ошибка при заполнении дыр: {e}")

        return self.mesh

    def clean_mesh(self):
        """
        Очищает mesh от артефактов: удаляет вырожденные треугольники,
        дублированные вершины и т.д.
        """
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

    def repair_mesh(self):
        """
        Комплексный метод восстановления mesh:
        - Очистка
        - Заполнение дыр
        - Сглаживание
        """
        if self.mesh is None:
            return None

        self.clean_mesh()
        self.fill_small_holes()
        self.smooth_mesh(iterations=3)

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
        return info