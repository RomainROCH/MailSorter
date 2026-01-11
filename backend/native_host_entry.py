import os
import sys

# Ensure the project root is on sys.path so we can import the `backend` package.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

from backend.main import main  # noqa: E402


if __name__ == "__main__":
    main()
