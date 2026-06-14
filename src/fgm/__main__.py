import sys
import os
from streamlit.web import cli as stcli


def main() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)

    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    sys.argv = ["streamlit", "run", "src/fgm/gui.py", "--global.developmentMode=false"]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
