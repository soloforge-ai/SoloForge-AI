import json
from pathlib import Path

from config import (
    OUTPUT_DIR,
    OUTPUT_PREFIX,
    CHUNK_SIZE,
)


class JsonlExporter:

    def __init__(self):

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        self.chunk_index = 1
        self.record_count = 0
        self.total_count = 0

        self.chunk_files = []

        self.file = None

        self._open_new_chunk()

    def _chunk_filename(self):

        return f"{OUTPUT_PREFIX}_{self.chunk_index:04d}.jsonl"

    def _open_new_chunk(self):

        if self.file:
            self.file.close()

        filename = self._chunk_filename()

        filepath = OUTPUT_DIR / filename

        self.chunk_files.append(filename)

        self.file = open(
            filepath,
            "w",
            encoding="utf-8",
        )

        self.record_count = 0

    def write(self, product):

        if self.record_count >= CHUNK_SIZE:

            self.chunk_index += 1

            self._open_new_chunk()

        self.file.write(
            json.dumps(
                product,
                ensure_ascii=False,
            )
        )

        self.file.write("\n")

        self.record_count += 1
        self.total_count += 1

    def close(self):

        if self.file:
            self.file.close()

    def __enter__(self):

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.close()