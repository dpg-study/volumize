import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

from core.mesh_generator import MeshGenerator


class MeshDialog(tk.Toplevel):
    """Диалог для создания mesh из облака точек"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Создание 3D-модели из облака точек")
        self.geometry("600x500")
        self.resizable(True, True)

        self.mesh_gen = MeshGenerator()
        self.input_file = None

        self.setup_ui()

    def setup_ui(self):
        # Основной фрейм
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === Входной файл ===
        input_frame = ttk.LabelFrame(main_frame, text="Входной файл (облако точек)", padding=5)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Button(input_frame, text="📂 Выбрать PLY файл",
                   command=self.select_input).pack(side=tk.LEFT, padx=5)

        self.input_label = ttk.Label(input_frame, text="Файл не выбран")
        self.input_label.pack(side=tk.LEFT, padx=10)

        # === Информация о файле ===
        info_frame = ttk.LabelFrame(main_frame, text="Информация", padding=5)
        info_frame.pack(fill=tk.X, pady=5)

        self.info_text = tk.Text(info_frame, height=3, state='disabled')
        self.info_text.pack(fill=tk.X, padx=5, pady=5)

        # === Метод реконструкции ===
        method_frame = ttk.LabelFrame(main_frame, text="Метод реконструкции", padding=5)
        method_frame.pack(fill=tk.X, pady=5)

        self.method_var = tk.StringVar(value="poisson")

        ttk.Radiobutton(method_frame, text="Poisson (лучший для замкнутых объектов)",
                        variable=self.method_var, value="poisson").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(method_frame, text="Alpha Shapes (для открытых поверхностей)",
                        variable=self.method_var, value="alpha").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(method_frame, text="Ball Pivoting (для органических форм)",
                        variable=self.method_var, value="ball").pack(anchor=tk.W, pady=2)

        # === Параметры ===
        params_frame = ttk.LabelFrame(main_frame, text="Параметры", padding=5)
        params_frame.pack(fill=tk.X, pady=5)

        # Глубина для Poisson
        poisson_frame = ttk.Frame(params_frame)
        poisson_frame.pack(fill=tk.X, pady=2)
        ttk.Label(poisson_frame, text="Глубина Poisson (8-12):").pack(side=tk.LEFT)
        self.depth_var = tk.IntVar(value=9)
        ttk.Spinbox(poisson_frame, from_=5, to=12, width=5,
                    textvariable=self.depth_var).pack(side=tk.LEFT, padx=5)

        # Альфа для Alpha Shapes
        alpha_frame = ttk.Frame(params_frame)
        alpha_frame.pack(fill=tk.X, pady=2)
        ttk.Label(alpha_frame, text="Alpha параметр:").pack(side=tk.LEFT)
        self.alpha_var = tk.DoubleVar(value=0.03)
        ttk.Entry(alpha_frame, textvariable=self.alpha_var, width=10).pack(side=tk.LEFT, padx=5)

        # === Пост-обработка ===
        post_frame = ttk.LabelFrame(main_frame, text="Пост-обработка", padding=5)
        post_frame.pack(fill=tk.X, pady=5)

        self.simplify_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(post_frame, text="Упростить модель (уменьшить полигоны)",
                        variable=self.simplify_var).pack(anchor=tk.W)

        self.smooth_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(post_frame, text="Сгладить поверхность",
                        variable=self.smooth_var).pack(anchor=tk.W)

        self.fill_holes_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(post_frame, text="Заполнить дыры",
                        variable=self.fill_holes_var).pack(anchor=tk.W)

        # === Кнопки ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        # СОЗДАЕМ КНОПКИ С СОХРАНЕНИЕМ В self
        self.generate_btn = ttk.Button(btn_frame, text="▶ Создать 3D-модель",
                                       command=self.generate_mesh)
        self.generate_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(btn_frame, text="💾 Сохранить как...",
                                   command=self.save_mesh, state='disabled')
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.view_btn = ttk.Button(btn_frame, text="👁 Просмотреть",
                                   command=self.view_mesh, state='disabled')
        self.view_btn.pack(side=tk.LEFT, padx=5)

        # === Прогресс ===
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)

        # === Лог ===
        log_frame = ttk.LabelFrame(main_frame, text="Лог", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def select_input(self):
        """Выбор входного PLY файла"""
        filename = filedialog.askopenfilename(
            title="Выберите PLY файл с облаком точек",
            filetypes=[
                ("PLY files", "*.ply"),
                ("XYZ files", "*.xyz"),
                ("PTS files", "*.pts"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.input_file = filename
            self.input_label.config(text=os.path.basename(filename))
            self.show_file_info()

    def show_file_info(self):
        """Показывает информацию о файле"""
        if self.mesh_gen.load_point_cloud(self.input_file):
            info = self.mesh_gen.get_info()
            self.log(f"✅ Файл загружен: {self.input_file}")
            self.log(f"📊 Количество точек: {info.get('points', 0)}")
        else:
            self.log("❌ Ошибка загрузки файла")

    def generate_mesh(self):
        """Запускает создание mesh"""
        if not self.input_file:
            messagebox.showerror("Ошибка", "Сначала выберите входной файл")
            return

        # Блокируем кнопку генерации
        self.generate_btn.config(state='disabled')
        self.save_btn.config(state='disabled')
        self.view_btn.config(state='disabled')
        self.progress.start()

        # Очищаем лог перед началом
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

        self.log("🚀 Запуск процесса создания 3D-модели...")
        self.log(f"📁 Файл: {os.path.basename(self.input_file)}")
        self.log(f"🔧 Метод: {self.method_var.get()}")

        def update_progress(message):
            """Обновление прогресса из потока"""
            self.after(0, lambda: self.log(message))

        def generate_thread():
            try:
                # Шаг 1: Загрузка облака точек
                update_progress("📂 Загрузка облака точек...")
                if not self.mesh_gen.load_point_cloud(self.input_file):
                    update_progress("❌ Ошибка загрузки файла")
                    return

                points_count = len(self.mesh_gen.pcd.points) if self.mesh_gen.pcd else 0
                update_progress(f"✅ Загружено {points_count} точек")

                # Шаг 2: Выбор метода
                method = self.method_var.get()

                if method == "poisson":
                    depth = self.depth_var.get()
                    update_progress(f"🔨 Poisson реконструкция (глубина {depth})...")
                    update_progress("⏳ Это может занять 5-10 минут...")

                    # Засекаем время
                    import time
                    start_time = time.time()

                    # Запускаем реконструкцию
                    self.mesh_gen.generate_mesh_poisson(depth=depth)

                    elapsed = time.time() - start_time
                    update_progress(f"✅ Poisson завершен за {elapsed:.1f} секунд")

                elif method == "alpha":
                    alpha = self.alpha_var.get()
                    update_progress(f"🔨 Alpha Shapes реконструкция (alpha={alpha})...")
                    self.mesh_gen.generate_mesh_alpha(alpha=alpha)

                elif method == "ball":
                    update_progress(f"🔨 Ball Pivoting реконструкция...")
                    self.mesh_gen.generate_mesh_ball_pivoting()

                # Шаг 3: Пост-обработка
                if self.mesh_gen.mesh:
                    update_progress("🔧 Применение пост-обработки...")

                    if self.simplify_var.get():
                        update_progress("  📉 Упрощение модели...")
                        self.mesh_gen.simplify_mesh()

                    if self.smooth_var.get():
                        update_progress("  ✨ Сглаживание...")
                        self.mesh_gen.smooth_mesh()

                    if self.fill_holes_var.get():
                        update_progress("  🕳️ Заполнение дыр...")
                        self.mesh_gen.fill_small_holes()

                    update_progress("  🧹 Очистка модели...")
                    self.mesh_gen.clean_mesh()

                    # Шаг 4: Результат
                    info = self.mesh_gen.get_info()
                    update_progress(f"✅ Модель успешно создана!")
                    update_progress(f"📊 Вершин: {info.get('vertices', 0)}")
                    update_progress(f"📊 Треугольников: {info.get('triangles', 0)}")

                    # Активируем кнопки
                    self.after(0, self.enable_save_buttons)
                else:
                    update_progress("❌ Не удалось создать модель")

            except Exception as e:
                import traceback
                error_msg = str(e)
                trace = traceback.format_exc()
                update_progress(f"❌ Ошибка: {error_msg}")
                print(trace)  # Печатаем в консоль для отладки
            finally:
                self.after(0, self.progress.stop)
                self.after(0, lambda: self.generate_btn.config(state='normal'))

        # Запускаем поток
        import threading
        thread = threading.Thread(target=generate_thread)
        thread.daemon = True
        thread.start()

        # Добавляем проверку через 30 секунд для отладки
        def check_timeout():
            if thread.is_alive():
                self.log("⏳ Процесс все еще выполняется... Это нормально для больших файлов.")
                self.log("💡 Poisson с depth=11 может занимать 5-15 минут.")

        self.after(30000, check_timeout)  # Проверка через 30 секунд

    def enable_save_buttons(self):
        """Активирует кнопки сохранения и просмотра"""
        self.save_btn.config(state='normal')
        self.view_btn.config(state='normal')
        self.log("✅ Кнопки сохранения и просмотра активированы")

    def save_mesh(self):
        """Сохраняет mesh в файл"""
        if not self.mesh_gen.mesh:
            return

        filename = filedialog.asksaveasfilename(
            title="Сохранить 3D-модель",
            defaultextension=".ply",
            filetypes=[
                ("PLY files", "*.ply"),
                ("OBJ files", "*.obj"),
                ("STL files", "*.stl"),
                ("All files", "*.*")
            ]
        )
        if filename:
            if self.mesh_gen.save_mesh(filename):
                self.log(f"💾 Модель сохранена: {filename}")
                messagebox.showinfo("Успех", f"Модель сохранена:\n{filename}")
            else:
                self.log("❌ Ошибка сохранения")

    def view_mesh(self):
        """Открывает mesh во вьювере"""
        if self.mesh_gen.mesh and hasattr(self.parent, 'main_window') and hasattr(self.parent.main_window, 'viewer'):
            import tempfile
            temp_file = os.path.join(tempfile.gettempdir(), 'temp_mesh.ply')
            self.mesh_gen.save_mesh(temp_file)
            self.parent.main_window.viewer.load_model(temp_file)
            self.parent.main_window.notebook.select(0)
            self.log("👁 Модель открыта в 3D вьювере")

    def log(self, message):
        """Добавляет сообщение в лог"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.update()