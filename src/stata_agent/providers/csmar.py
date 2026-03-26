from pathlib import Path

from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.fetch.types import QueryPlan


class CsmarMetadataError(RuntimeError):
    pass


class _CatalogField:
    def __init__(
        self,
        *,
        table_name: str,
        field_name: str,
        database: str,
        aliases: tuple[str, ...],
        frequency_tags: tuple[str, ...],
    ) -> None:
        self.table_name = table_name
        self.field_name = field_name
        self.database = database
        self.aliases = aliases
        self.frequency_tags = frequency_tags


_DEFAULT_CATALOG: tuple[_CatalogField, ...] = (
    _CatalogField(
        table_name="FS_Comins",
        field_name="ROA",
        database="财务报表",
        aliases=("roa", "资产回报率", "总资产收益率"),
        frequency_tags=("annual", "quarterly"),
    ),
    _CatalogField(
        table_name="BANK_DIGITAL_INDEX",
        field_name="DIGITAL_INDEX",
        database="银行专题",
        aliases=("数字化转型指数", "数字化指数", "digital transformation index"),
        frequency_tags=("annual", "quarterly"),
    ),
    _CatalogField(
        table_name="FS_Combas",
        field_name="CAPITAL_ADEQUACY",
        database="财务报表",
        aliases=("资本充足率", "资本充足"),
        frequency_tags=("annual", "quarterly"),
    ),
    _CatalogField(
        table_name="BANK_RISK",
        field_name="LLR_COVERAGE",
        database="银行专题",
        aliases=("拨备覆盖率",),
        frequency_tags=("annual", "quarterly"),
    ),
    _CatalogField(
        table_name="FS_Combas",
        field_name="ASSET",
        database="财务报表",
        aliases=("资产规模", "总资产"),
        frequency_tags=("annual", "quarterly"),
    ),
)


class CsmarBridgeClient:
    def __init__(
        self,
        catalog: tuple[_CatalogField, ...] = _DEFAULT_CATALOG,
        *,
        query_count_overrides: dict[tuple[str, str], int] | None = None,
        inaccessible_fields: set[tuple[str, str]] | None = None,
    ) -> None:
        self._catalog = catalog
        self._query_count_overrides = query_count_overrides or {}
        self._inaccessible_fields = inaccessible_fields or set()

    def fetch(self, plan: QueryPlan, output_dir: Path) -> Path:
        return output_dir / f"{plan.table_name}.parquet"

    def find_field_candidates(self, variable_name: str) -> list[CsmarFieldCandidate]:
        normalized_name = variable_name.strip().lower()
        if not normalized_name:
            raise CsmarMetadataError("变量名为空，无法检索 CSMAR 字段候选。")

        matches = [
            item
            for item in self._catalog
            if normalized_name in {alias.lower() for alias in item.aliases}
            or normalized_name in item.field_name.lower()
        ]
        return [
            CsmarFieldCandidate(
                variable_name=variable_name,
                table_name=item.table_name,
                field_name=item.field_name,
                csmar_database=item.database,
                alias_hit=normalized_name in {alias.lower() for alias in item.aliases},
                frequency_tags=list(item.frequency_tags),
            )
            for item in matches
        ]

    def field_exists(self, table_name: str, field_name: str) -> bool:
        return any(
            item.table_name == table_name and item.field_name == field_name
            for item in self._catalog
        )

    def query_count(self, table_name: str, field_name: str) -> int:
        key = (table_name, field_name)
        if key in self._inaccessible_fields:
            raise CsmarMetadataError(
                f"字段不可访问：{table_name}.{field_name} 无法执行 queryCount 探针。"
            )

        if key in self._query_count_overrides:
            return self._query_count_overrides[key]

        if self.field_exists(table_name, field_name):
            return 100
        raise CsmarMetadataError(f"字段不存在：{table_name}.{field_name}")
