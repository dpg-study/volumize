import os
import sys


class Config:
    @staticmethod
    def get_colmap_path():
        """Возвращает путь к colmap.exe"""
        # Путь к COLMAP в вашем проекте
        base_path = os.path.dirname(os.path.abspath(__file__))

        # Правильный путь к colmap.exe
        colmap_exe = os.path.join(base_path, "colmap_bin", "bin", "colmap.exe")

        if os.path.exists(colmap_exe):
            return colmap_exe

        # Если не нашли, пробуем другие варианты
        alt_path = os.path.join(base_path, "colmap_bin", "COLMAP.bat")
        if os.path.exists(alt_path):
            return alt_path

        return None

    MIN_PHOTOS = 15
    MAX_IMAGE_SIZE = 4000