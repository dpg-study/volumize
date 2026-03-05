import subprocess
import os
import sys
import glob
import time


class COLMAPRunner:
    """
    Класс для запуска COLMAP реконструкции
    """

    def __init__(self, config):
        self.config = config
        self.process = None
        self.is_running = False
        self.colmap_path = config.get_colmap_path()
        if self.colmap_path and os.path.exists(self.colmap_path):
            colmap_dir = os.path.dirname(os.path.dirname(self.colmap_path))
            plugins_dir = os.path.join(colmap_dir, "plugins")
            if os.path.exists(plugins_dir):
                print(f"✅ COLMAP инициализирован. Плагины в: {plugins_dir}")
            else:
                print(f"⚠️ Плагины не найдены в: {plugins_dir}")
    def run_full_pipeline(self, image_dir, output_dir, callback):
        """
        Запускает полный пайплайн COLMAP реконструкции
        """
        self.is_running = True
        colmap_dir = os.path.dirname(self.colmap_path)
        plugins_path = os.path.join(colmap_dir, "plugins")
        if os.path.exists(plugins_path):
            callback(f"✅ Найдены плагины Qt: {plugins_path}", 0)
        else:
            callback(f"⚠️ Папка с плагинами Qt не найдена: {plugins_path}", 0)
            callback(f"⚠️ Возможны проблемы с графическим интерфейсом", 0)
        # ПРОВЕРКА: что за пути нам передали?
        callback(f"📁 Входная папка с фото: {image_dir}", 0)
        callback(f"📁 Выходная папка: {output_dir}", 0)

        if not self.colmap_path:
            callback("❌ COLMAP не найден! Укажите путь в настройках.", 0)
            return False

        # Проверяем наличие фотографий (ищем все возможные расширения)
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        images = []
        for ext in image_extensions:
            images.extend(glob.glob(os.path.join(image_dir, ext)))

        callback(f"📸 Найдено фотографий: {len(images)}", 5)

        if len(images) < self.config.MIN_PHOTOS:
            callback(f"❌ Слишком мало фото: {len(images)}. Нужно минимум {self.config.MIN_PHOTOS}", 0)
            return False

        # Нормализуем пути (убираем возможные проблемы с слешами)
        image_dir = os.path.normpath(image_dir)
        output_dir = os.path.normpath(output_dir)

        # Создаем структуру папок
        database_path = os.path.join(output_dir, "database.db")
        sparse_dir = os.path.join(output_dir, "sparse")
        dense_dir = os.path.join(output_dir, "dense")

        os.makedirs(sparse_dir, exist_ok=True)
        os.makedirs(dense_dir, exist_ok=True)

        # Убедимся, что папка с фото существует
        if not os.path.exists(image_dir):
            callback(f"❌ Папка с фото не существует: {image_dir}", 0)
            return False

        callback(f"✅ Папка с фото существует: {image_dir}", 0)
        callback(f"✅ Первые 5 фото: {[os.path.basename(f) for f in images[:5]]}", 0)

        # Шаг 1: Извлечение признаков
        callback("🔍 Шаг 1/6: Извлечение признаков (Feature Extraction)...", 10)
        cmd = [
            self.colmap_path, "feature_extractor",
            "--database_path", database_path,
            "--image_path", image_dir
        ]
        callback(f"  > {' '.join(cmd)}", None)

        if not self._run_command(cmd, callback):
            return False


        # Шаг 2: Сопоставление признаков
        callback("🔄 Шаг 2/6: Сопоставление признаков (Feature Matching)...", 30)
        cmd = [
            self.colmap_path, "exhaustive_matcher",
            "--database_path", database_path,
            "--SiftMatching.use_gpu", "1",
            "--SiftMatching.gpu_index", "0"
        ]
        callback(f"  > {' '.join(cmd)}", None)

        if not self._run_command(cmd, callback):
            return False

        # Шаг 3: Построение разреженной модели
        callback("📐 Шаг 3/6: Построение разреженной модели (SfM)...", 50)
        cmd = [
            self.colmap_path, "mapper",
            "--database_path", database_path,
            "--image_path", image_dir,
            "--output_path", sparse_dir
        ]
        callback(f"  > {' '.join(cmd)}", None)

        if not self._run_command(cmd, callback):
            return False

        # Находим папку с результатом (обычно "0" или другая цифра)
        sparse_result = None
        for item in os.listdir(sparse_dir):
            item_path = os.path.join(sparse_dir, item)
            if os.path.isdir(item_path):
                sparse_result = item_path
                break

        if not sparse_result:
            callback("❌ Ошибка: не удалось найти результат SfM", 0)
            return False

        callback(f"✅ Найдена SfM модель: {sparse_result}", 60)

        # Шаг 4: Подготовка изображений для плотной реконструкции
        callback("🖼️ Шаг 4/6: Подготовка изображений...", 70)
        cmd = [
            self.colmap_path, "image_undistorter",
            "--image_path", image_dir,
            "--input_path", sparse_result,
            "--output_path", dense_dir,
            "--output_type", "COLMAP"
        ]
        callback(f"  > {' '.join(cmd)}", None)

        if not self._run_command(cmd, callback):
            return False

        # Шаг 5: Плотная реконструкция
        callback("✨ Шаг 5/6: Плотная реконструкция (может занять время)...", 80)
        cmd = [
            self.colmap_path, "patch_match_stereo",
            "--workspace_path", dense_dir,
            "--workspace_format", "COLMAP",
            "--PatchMatchStereo.geom_consistency", "true",
            "--PatchMatchStereo.gpu_index", "0"  # <--- ДОБАВЬ ЭТУ СТРОКУ (не забудь запятую выше)
        ]
        callback(f"  > {' '.join(cmd)}", None)

        if not self._run_command(cmd, callback):
            return False

        # Шаг 6: Создание облака точек
        callback("☁️ Шаг 6/6: Создание облака точек...", 95)
        output_ply = os.path.join(dense_dir, "fused.ply")
        cmd = [
            self.colmap_path, "stereo_fusion",
            "--workspace_path", dense_dir,
            "--workspace_format", "COLMAP",
            "--input_type", "geometric",
            "--output_path", output_ply
        ]
        callback(f"  > {' '.join(cmd)}", None)

        if not self._run_command(cmd, callback):
            return False

        if os.path.exists(output_ply):
            callback(f"✅ Готово! Модель: {output_ply}", 100)
            return True
        else:
            callback("❌ Ошибка: файл модели не создан", 0)
            return False

    def _run_command(self, cmd, callback):
        """Запуск команды с логированием"""
        try:
            # Находим правильную папку с плагинами Qt
            colmap_exe_dir = os.path.dirname(self.colmap_path)  # D:\LABS\kosianik\colmap_bin\bin
            colmap_root = os.path.dirname(colmap_exe_dir)  # D:\LABS\kosianik\colmap_bin

            # Плагины находятся в корне colmap_bin, а не в bin!
            plugins_path = os.path.join(colmap_root, "plugins")

            callback(f"  🔍 Поиск плагинов в: {plugins_path}", None)

            # Настраиваем окружение
            env = os.environ.copy()
            if os.path.exists(plugins_path):
                env['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugins_path
                callback(f"  ✅ Плагины Qt найдены: {plugins_path}", None)

                # Проверяем наличие platforms
                platforms_path = os.path.join(plugins_path, "platforms")
                if os.path.exists(platforms_path):
                    callback(f"  ✅ Папка platforms существует", None)
                    platform_files = os.listdir(platforms_path)
                    callback(f"  📋 Файлы platforms: {platform_files}", None)
            else:
                callback(f"  ❌ Плагины Qt не найдены по пути: {plugins_path}", None)
                # Пробуем другие варианты
                alt_path = os.path.join(colmap_exe_dir, "plugins")
                if os.path.exists(alt_path):
                    env['QT_QPA_PLATFORM_PLUGIN_PATH'] = alt_path
                    callback(f"  ✅ Альтернативный путь: {alt_path}", None)

            # Пробуем разные платформы
            platforms_to_try = ['windows', 'offscreen', 'minimal']

            for platform in platforms_to_try:
                env['QT_QPA_PLATFORM'] = platform
                callback(f"  🖥️ Пробуем платформу: {platform}", None)

                try:
                    self.process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1,
                        encoding='utf-8',
                        errors='ignore',
                        env=env,
                        cwd=colmap_root  # Запускаем из корня colmap_bin
                    )

                    # Даем процессу время на запуск
                    time.sleep(1)

                    # Проверяем, запустился ли процесс
                    if self.process.poll() is None:
                        callback(f"  ✅ Успешно запущено с платформой: {platform}", None)
                        break
                    else:
                        # Процесс сразу завершился, пробуем другую платформу
                        continue

                except Exception as e:
                    callback(f"  ⚠️ Ошибка с платформой {platform}: {str(e)[:50]}", None)
                    continue

            # Читаем вывод
            output_lines = []
            for line in self.process.stdout:
                if not self.is_running:
                    self.process.terminate()
                    callback("⛔ Процесс остановлен", 0)
                    return False

                line = line.strip()
                if line:
                    output_lines.append(line)
                    if any(key in line.lower() for key in ['error', 'fail', 'cannot']):
                        callback(f"    ⚠️ {line}", None)
                    elif 'extract' in line.lower() or 'match' in line.lower():
                        callback(f"    {line}", None)

            returncode = self.process.wait()
            if returncode != 0:
                callback(f"    ❌ Команда завершилась с ошибкой (код {returncode})", 0)
                if output_lines:
                    callback(f"    📋 Последние строки вывода:", 0)
                    for line in output_lines[-10:]:
                        callback(f"      {line}", 0)
                return False

            return True

        except Exception as e:
            callback(f"❌ Ошибка: {str(e)}", 0)
            return False

    def stop(self):
        """Остановка процесса"""
        self.is_running = False
        if self.process:
            self.process.terminate()
            self.process = None
