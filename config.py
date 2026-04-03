import os
import sys


class Config:
    @staticmethod
    def get_colmap_path():

        base_path = os.path.dirname(os.path.abspath(__file__))


        colmap_exe = os.path.join(base_path, "colmap_bin", "bin", "colmap.exe")

        if os.path.exists(colmap_exe):
            return colmap_exe


        alt_path = os.path.join(base_path, "colmap_bin", "COLMAP.bat")
        if os.path.exists(alt_path):
            return alt_path

        return None

    MIN_PHOTOS = 15
    MAX_IMAGE_SIZE = 2500