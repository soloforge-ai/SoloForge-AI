import json
from datetime import datetime

from config import MANIFEST_FILE


def write_manifest(exporter):
    """
    Write manifest.json after export completes.
    """

    manifest = {
        "version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_products": exporter.total_count,
        "total_chunks": len(exporter.chunk_files),
        "chunk_size": exporter.record_count,
        "chunks": exporter.chunk_files,
    }

    with open(
        MANIFEST_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            manifest,
            f,
            ensure_ascii=False,
            indent=4,
        )