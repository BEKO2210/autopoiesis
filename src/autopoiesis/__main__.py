"""Allow `python -m autopoiesis`."""

import sys

from .cli import main

sys.exit(main())
