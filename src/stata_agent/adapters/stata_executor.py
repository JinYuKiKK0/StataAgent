from pathlib import Path


class StataExecutorClient:
    def run(self, do_file: Path) -> Path:
        return do_file.with_suffix(".log")

