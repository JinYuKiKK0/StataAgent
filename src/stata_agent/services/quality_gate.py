from pathlib import Path


class QualityGate:
    def validate(self, dataset_path: Path) -> Path:
        return dataset_path
