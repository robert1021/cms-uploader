import subprocess
import shutil
import os
import sys
from config import APP_NAME

if __name__ == "__main__":
    # PyInstaller --add-data separator is OS-specific: ; on Windows, : on POSIX
    sep = ";" if sys.platform == "win32" else ":"
    # Use --hidden-import for py modules (not --add-data) and --collect-all for packages with data/submodules
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name", APP_NAME,
        # project modules that are imported dynamically (main.py delays 'import app')
        "--hidden-import", "app",
        "--hidden-import", "config",
        "--hidden-import", "constants",
        "--hidden-import", "enums",
        "--hidden-import", "gui",
        "--hidden-import", "map_path_builder",
        "--hidden-import", "path_finder",
        "--hidden-import", "utils",
        # runtime deps
        "--collect-all", "openpyxl",
        "--collect-all", "rich",
        "--collect-all", "et_xmlfile",
        "--copy-metadata", "openpyxl",
        "--copy-metadata", "rich",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "tkinter.messagebox",
        "main.py",
    ]
    # Only bundle non-py assets here if you have icons/data; .py files are already handled as hiddenimports
    # Example: if you later add an icon:
    # cmd[4:4] = ["--add-data", f"assets{sep}."]

    print("Running:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    subprocess.run(cmd, text=True, check=True)

    shutil.rmtree("build", ignore_errors=True)
    # PyInstaller writes <APP_NAME>.spec (with space) in cwd
    spec = f"{APP_NAME}.spec"
    if os.path.exists(spec):
        os.remove(spec)
    elif os.path.exists("main.spec"):
        os.remove("main.spec")

    # pyinstaller with --name APP_NAME creates dist/<APP_NAME> or dist/<APP_NAME>.exe
    # Normalize to a single artifact next to the project
    src_exe = os.path.join("dist", f"{APP_NAME}.exe")
    src_bin = os.path.join("dist", APP_NAME)
    # On Linux the output has no .exe; keep it extensionless so `file` reports ELF, but also allow .exe alias for docs
    if os.path.exists(src_exe):
        dest = f"{APP_NAME}.exe"
        if os.path.abspath(src_exe) != os.path.abspath(dest):
            shutil.move(src_exe, dest)
    elif os.path.exists(src_bin):
        # Linux onefile: no extension unless we cross-build with Wine
        dest = APP_NAME if sys.platform != "win32" else f"{APP_NAME}.exe"
        if os.path.abspath(src_bin) != os.path.abspath(dest):
            shutil.move(src_bin, dest)
    shutil.rmtree("dist", ignore_errors=True)
    print(f"Done — artifact: {dest if 'dest' in locals() else 'check dist/'}")
