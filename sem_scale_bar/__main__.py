import sys

from sem_scale_bar.cli import main as cli_main


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if "--headless" in args:
        args.remove("--headless")
        return cli_main(args)

    try:
        from sem_scale_bar.gui import run_gui

        run_gui()
        return 0
    except ImportError:
        print("FreeSimpleGUI not available. Falling back to CLI usage.")
        return cli_main(args)


if __name__ == "__main__":
    sys.exit(main())
