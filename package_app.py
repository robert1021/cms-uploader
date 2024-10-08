import subprocess
import shutil
import os

if __name__ == "__main__":
    try:
        process = subprocess.run([
            "pyinstaller",
            "--onefile",
            "--add-data", r"enums.py;.",
            "--add-data", r"constants.py;.",
            "--add-data", r"map_path_builder.py;.",
            "--add-data", r"path_finder.py;.",
            "--hidden-import=openpyxl",
            "--hidden-import=rich",
            "--hidden-import=logging",
            "main.py"
        ], text=True, check=True)

        shutil.rmtree("build")
        os.remove("main.spec")
        os.rename("dist/main.exe", f"CMS Automation Tool.exe")
        shutil.rmtree("dist")

    except Exception as e:
        print("Error:", e)