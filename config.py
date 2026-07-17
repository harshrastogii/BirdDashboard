"""
DEPRECATED compatibility shim.

Configuration has moved into the birddash package. Import it as:

    from birddash import config

This module re-exports birddash.config so any lingering `import config`
continues to work. It is scheduled for removal — please update imports.
"""

from birddash.config import *  # noqa: F401,F403  (re-export public constants)
from birddash import config as _config

# Re-export everything (including names `import *` skips) so attribute access
# on this shim matches birddash.config exactly.
for _name in dir(_config):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_config, _name)
