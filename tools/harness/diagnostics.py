from dataclasses import dataclass


@dataclass(slots=True)
class Diagnostic:
    code: str
    path: str
    message: str
    why: str
    fix: str

    def render(self) -> str:
        return "\n".join(
            [
                f"{self.code} {self.message}",
                f"Found: {self.path}",
                f"Why: {self.why}",
                f"Fix: {self.fix}",
            ]
        )
