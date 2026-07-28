"""Foldok capture bridge — the folder is the bus.

    publish(folder, tasks_from_gaps(session.gaps()), project_id=...)   desktop -> phone
    ingest(folder, session)                                            phone -> desktop

No pairing, no QR, no server. The Capture app already binds a project to a SAF
folder (OneDrive, Drive, local), so the photo reaches the laptop through the
customer's own approved sync tool and Foldok never touches the network.
"""

from .bridge import (
    Capture,
    IngestReport,
    Issue,
    bind,
    ingest,
    publish,
    read_binding,
    read_tasks,
    scan,
    tasks_from_gaps,
)
from .model import (
    BINDING_FILE,
    FOLDOK_DIR,
    SCHEMA_VERSION,
    SIDECAR_SUFFIX,
    TASKS_FILE,
    Binding,
    CaptureTask,
    Sidecar,
    TaskList,
    checksum_of,
    folder_paths,
    is_capture,
    sidecar_name,
)

__all__ = [
    "BINDING_FILE", "Binding", "Capture", "CaptureTask", "FOLDOK_DIR", "IngestReport",
    "Issue", "SCHEMA_VERSION", "SIDECAR_SUFFIX", "Sidecar", "TASKS_FILE", "TaskList",
    "bind", "checksum_of", "folder_paths", "ingest", "is_capture", "publish",
    "read_binding", "read_tasks", "scan", "sidecar_name", "tasks_from_gaps",
]

__version__ = "0.78.0"
