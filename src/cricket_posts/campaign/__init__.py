"""Compatibility imports for the pre-reorganization campaign package.

New application code should import from :mod:`advantage`. This module remains
temporarily so existing scripts and integrations can migrate without a flag day.
"""

from advantage import *  # noqa: F401,F403
from advantage import __all__
