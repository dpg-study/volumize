import subprocess
import os
import sys
import glob
import time


class COLMAPRunner:
    def __init__(self, config):
        self.config = config
        self.process = None
        self.is_running = False
        self.colmap_path = config.get_colmap_path()

    def run_full_pipeline(self, image_dir, output_dir, callback):
        self.is_running = True
        colmap_dir = os.path.dirname(self.colmap_path)
        plugins_path = os.path.join(colmap_dir, "plugins")

        env = os.environ.copy()
        if os.path.exists(plugins_path):
            env["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugins_path

        db_path = os.path.join(output_dir, "database.db")
        sparse_path = os.path.join(output_dir, "sparse")
        dense_path = os.path.join(output_dir, "dense")

        for d in [sparse_path, dense_path]:
            os.makedirs(d, exist_ok=True)

        steps = [
            ["feature_extractor", "--database_path", db_path, "--image_path", image_dir, "--ImageReader.single_camera",
             "1"],
            ["exhaustive_matcher", "--database_path", db_path],
            ["mapper", "--database_path", db_path, "--image_path", image_dir, "--output_path", sparse_path],
            ["image_undistorter", "--image_path", image_dir, "--input_path", os.path.join(sparse_path, "0"),
             "--output_path", dense_path, "--output_type", "COLMAP"],
            ["patch_match_stereo", "--workspace_path", dense_path, "--PatchMatchStereo.geom_consistency", "true"],
            ["stereo_fusion", "--workspace_path", dense_path, "--output_path", os.path.join(output_dir, "result.ply")]
        ]

        for i, args in enumerate(steps):
            if not self.is_running: break
            callback(f"Шаг {i + 1}/6: {args[0]}", (i / 6) * 100)
            if not self.run_command([self.colmap_path] + args, callback, env):
                self.is_running = False
                return False

        self.is_running = False
        callback("Готово", 100)
        return True

    def run_command(self, cmd, callback, env):
        try:
            callback(f"> {' '.join(cmd)}", None)

            platforms = ['windows', 'offscreen', 'minimal']
            success = False

            for platform in platforms:
                current_env = env.copy()
                current_env["QT_QPA_PLATFORM"] = platform

                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    encoding='utf-8',
                    env=current_env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )

                output_lines = []
                for line in self.process.stdout:
                    if not self.is_running:
                        self.process.terminate()
                        return False

                    line = line.strip()
                    if line:
                        output_lines.append(line)
                        if any(k in line.lower() for k in ['extract', 'match', 'image']):
                            callback(f"    {line}", None)

                returncode = self.process.wait()
                if returncode == 0:
                    success = True
                    break
                elif returncode == 3221226505 or "opengl" in "".join(output_lines).lower():
                    continue
                else:
                    break

            return success
        except Exception as e:
            callback(f"Ошибка: {str(e)}", 0)
            return False

    def stop(self):
        self.is_running = False
        if self.process:
            self.process.terminate()