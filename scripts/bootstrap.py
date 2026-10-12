"""Install everything MyEdgeSimPy needs.

EdgeSimPy is not published on PyPI, so it is installed straight from GitHub:

    python scripts/bootstrap.py

If the machine has no network access, clone the repository manually and install the
local copy instead:

    git clone https://github.com/EdgeSimPy/EdgeSimPy.git .third_party/EdgeSimPy
    python scripts/bootstrap.py --from-vendor
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR_DIR = REPO_ROOT / ".third_party" / "EdgeSimPy"
EDGESIMPY_GIT = "git+https://github.com/EdgeSimPy/EdgeSimPy.git"


def run(command, **kwargs) -> None:
    print("$ " + " ".join(command))
    subprocess.check_call(command, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-vendor",
        action="store_true",
        help="install EdgeSimPy from the local .third_party/EdgeSimPy checkout",
    )
    parser.add_argument("--no-requirements", action="store_true", help="skip requirements.txt")
    args = parser.parse_args()

    python = sys.executable

    if not args.no_requirements:
        run([python, "-m", "pip", "install", "-q", "-r", str(REPO_ROOT / "requirements.txt")])

    if args.from_vendor:
        if not VENDOR_DIR.exists():
            raise SystemExit(
                f"{VENDOR_DIR} does not exist. Clone EdgeSimPy there first, or run without --from-vendor."
            )
        run([python, "-m", "pip", "install", "-q", "-e", str(VENDOR_DIR)])
    else:
        run([python, "-m", "pip", "install", "-q", EDGESIMPY_GIT])

    run([python, "-c", "import edge_sim_py; print('EdgeSimPy', edge_sim_py.__version__)"])
    print("\nBootstrap complete. Try:  python -m myedgesimpy inspect --config configs/small.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())