from pathlib import Path

from stata_agent.domains.fetch.types import QueryPlan


class CsmarBridgeClient:
    def fetch(self, plan: QueryPlan, output_dir: Path) -> Path:
        return output_dir / f"{plan.table_name}.parquet"
