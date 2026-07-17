"""Repositories: the storage-abstraction seam.

Metadata repositories query Postgres; the detection repository reads artifacts
from the filesystem. In Phase 6 the filesystem adapters are replaced by
database/object-storage adapters WITHOUT changing the service or API layers.
"""
