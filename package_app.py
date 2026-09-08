import subprocess
import shutil
import os
from config import APP_NAME

if __name__ == "__main__":
    try:
        process = subprocess.run([
            "pyinstaller",
            "--noconsole",
            "--onefile",
            "--name", APP_NAME,
            "--add-data", r"enums.py;.",
            "--add-data", r"constants.py;.",
            "--add-data", r"config.py;.",
            "--add-data", r"utils.py;.",
            "--add-data", r"map_path_builder.py;.",
            "--add-data", r"path_finder.py;.",
            "--add-data", r"gui.py;.",
            "--hidden-import=openpyxl",
            "--hidden-import=rich",
            "--hidden-import=logging",
            "--hidden-import=tkinter",
            "--hidden-import=tkinter.ttk",
            "--hidden-import=tkinter.filedialog",
            "--hidden-import=tkinter.messagebox",
            "--hidden-import=shutil",
            "--hidden-import=typing",
            "--hidden-import=subprocess",
            "--hidden-import=re",
            "--hidden-import=os",
            "--hidden-import=queue",
            "--hidden-import=threading",
            "main.py"
        ], text=True, check=True)

        shutil.rmtree("build", ignore_errors=True)
        spec = f"{APP_NAME}.spec"
        if os.path.exists(spec):
            os.remove(spec)
        elif os.path.exists("main.spec"):
            os.remove("main.spec")
        # pyinstaller with --name APP_NAME creates dist/<APP_NAME>.exe on Windows, dist/<APP_NAME> on Linux
        src_exe = os.path.join("dist", f"{APP_NAME}.exe")
        src_bin = os.path.join("dist", APP_NAME)
        if os.path.exists(src_exe):
            os.rename(src_exe, f"{APP_NAME}.exe")
        elif os.path.exists(src_bin):
            os.rename(src_bin, f"{APP_NAME}.exe" if os.name == "nt" else APP_NAME)
        shutil.rmtree("dist", ignore_errors=True)

    except Exception as e:
        print("Error:", e)