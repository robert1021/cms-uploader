import sys

if __name__ == "__main__":
    # GUI by default; --tui keeps legacy rich/tkinter hybrid for headless/debug
    if "--tui" in sys.argv:
        from app import run_app
        run_app()
    else:
        try:
            from gui import main as gui_main
            gui_main()
        except ModuleNotFoundError as e:
            # tkinter missing (WSL/container without python3-tk) — fall back to TUI with hint
            if "tkinter" in str(e):
                print("tkinter not found (needs python3-tk / python3.14-tk). Falling back to TUI.")
                print("On Ubuntu/WSL: sudo apt install python3-tk python3.14-tk")
                print("Or run with bundled .exe on Windows where tkinter is included.")
                from app import run_app
                run_app()
            else:
                raise
        except Exception as e:
            # No display (e.g. SSH without X) — fall back to TUI
            if "no display" in str(e).lower() or "couldn't connect to display" in str(e).lower():
                print(f"GUI unavailable ({e}), falling back to TUI.")
                from app import run_app
                run_app()
            else:
                raise
