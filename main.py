"""Entry point: python main.py [COMMAND] [OPTIONS]"""

import sys

from expense_tracker.cli import main

if __name__ == "__main__":
    sys.exit(main())
