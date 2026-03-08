import csv
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .jurisdictions import (
    JURISDICTIONS_BY_CODE,
    NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS,
)
from .runtime_paths import data_dir

logger = logging.getLogger(__name__)

MIN_CHILD_SUPPORT_INCOME = 12_000
SIMPLIFIED_TABLE_MAX_INCOME = 150_000


@dataclass(frozen=True)
class Over150kRule:
    base_amount: float
    plus_pct: float
    income_over: float = SIMPLIFIED_TABLE_MAX_INCOME


@dataclass(frozen=True)
class ChildSupportTable:
    jurisdiction_code: str
    jurisdiction_name: str
    lookup_by_children: dict[int, dict[int, float]]
    over_150k_rules: dict[int, Over150kRule]
    child_aliases: dict[int, int] = field(default_factory=dict)

    def available_children(self) -> list[int]:
        available = set(self.lookup_by_children) | set(self.child_aliases)
        return sorted(available)

    def normalized_children(self, num_children: int) -> int:
        normalized_children = self.child_aliases.get(num_children, num_children)
        if normalized_children not in self.lookup_by_children:
            raise ValueError(
                f"No support rules were found for {num_children} children in {self.jurisdiction_name}."
            )
        return normalized_children

    def rounded_income(self, income: float) -> int | None:
        if income < MIN_CHILD_SUPPORT_INCOME:
            return None
        if income > SIMPLIFIED_TABLE_MAX_INCOME:
            return None

        rounded_income = int(((income + 50) // 100) * 100)
        return min(max(rounded_income, MIN_CHILD_SUPPORT_INCOME), SIMPLIFIED_TABLE_MAX_INCOME)

    def amount(self, num_children: int, income: float) -> float:
        if income < 0:
            raise ValueError("Income must be zero or greater.")

        normalized_children = self.normalized_children(num_children)
        rounded_income = self.rounded_income(income)
        if rounded_income is not None:
            amount = self.lookup_by_children[normalized_children].get(rounded_income, 0.0)
            logger.debug(
                "Child support lookup hit simplified table: jurisdiction=%s children=%s income=%s rounded=%s amount=%s",
                self.jurisdiction_code,
                normalized_children,
                income,
                rounded_income,
                amount,
            )
            return round(amount, 2)

        if income < MIN_CHILD_SUPPORT_INCOME:
            logger.debug(
                "Income %s falls below the simplified table minimum for %s.",
                income,
                self.jurisdiction_code,
            )
            return 0.0

        rule = self.over_150k_rules[normalized_children]
        amount = rule.base_amount + (income - rule.income_over) * rule.plus_pct / 100.0
        logger.debug(
            "Child support calculated from over-150k rule: jurisdiction=%s children=%s income=%s amount=%s",
            self.jurisdiction_code,
            normalized_children,
            income,
            amount,
        )
        return round(max(amount, 0.0), 2)


@dataclass(frozen=True)
class ChildSupportTableRegistry:
    tables_by_jurisdiction: dict[str, ChildSupportTable]

    def supported_jurisdictions(self) -> list[dict[str, str]]:
        supported = []
        for jurisdiction in NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS:
            if jurisdiction.code in self.tables_by_jurisdiction:
                supported.append(
                    {"code": jurisdiction.code, "name": jurisdiction.name}
                )
        return supported

    def for_jurisdiction(self, jurisdiction_code: str) -> ChildSupportTable:
        normalized_code = jurisdiction_code.upper()
        if normalized_code not in self.tables_by_jurisdiction:
            raise ValueError(f"Unsupported jurisdiction code '{jurisdiction_code}'.")

        logger.debug("Selected child-support table for jurisdiction %s.", normalized_code)
        return self.tables_by_jurisdiction[normalized_code]

    def supported_children(self) -> list[int]:
        if not self.tables_by_jurisdiction:
            return []

        first_table = next(iter(self.tables_by_jurisdiction.values()))
        return first_table.available_children()


def load_child_support_registry(
    lookup_csv_path: Path,
    over_150k_csv_path: Path,
) -> ChildSupportTableRegistry:
    logger.info(
        "Loading child support lookup tables from %s and %s",
        lookup_csv_path,
        over_150k_csv_path,
    )
    if not lookup_csv_path.exists():
        raise FileNotFoundError(f"Support lookup table not found at {lookup_csv_path}")
    if not over_150k_csv_path.exists():
        raise FileNotFoundError(f"Support over-150k table not found at {over_150k_csv_path}")

    lookup_by_jurisdiction: dict[str, dict[int, dict[int, float]]] = {}
    with lookup_csv_path.open(newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            jurisdiction_code = row["Jurisdiction"]
            children = int(row["Children"])
            income = int(row["Income"])
            amount = float(row["Amount"])
            lookup_by_jurisdiction.setdefault(jurisdiction_code, {}).setdefault(
                children, {}
            )[income] = amount

    over_150k_rules_by_jurisdiction: dict[str, dict[int, Over150kRule]] = {}
    with over_150k_csv_path.open(newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            jurisdiction_code = row["Jurisdiction"]
            children = int(row["Children"])
            over_150k_rules_by_jurisdiction.setdefault(jurisdiction_code, {})[children] = (
                Over150kRule(
                    base_amount=float(row["BasicAmount"]),
                    plus_pct=float(row["PlusPct"]),
                    income_over=float(row["OfIncomeOver"]),
                )
            )

    tables_by_jurisdiction: dict[str, ChildSupportTable] = {}
    for jurisdiction in NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS:
        lookup_by_children = lookup_by_jurisdiction.get(jurisdiction.code)
        over_150k_rules = over_150k_rules_by_jurisdiction.get(jurisdiction.code)
        if not lookup_by_children or not over_150k_rules:
            raise ValueError(
                f"Incomplete child-support data for jurisdiction {jurisdiction.code}."
            )

        child_aliases = {7: 6} if 6 in lookup_by_children else {}
        tables_by_jurisdiction[jurisdiction.code] = ChildSupportTable(
            jurisdiction_code=jurisdiction.code,
            jurisdiction_name=jurisdiction.name,
            lookup_by_children=lookup_by_children,
            over_150k_rules=over_150k_rules,
            child_aliases=child_aliases,
        )

    logger.info(
        "Loaded child support tables for jurisdictions: %s",
        sorted(tables_by_jurisdiction),
    )
    return ChildSupportTableRegistry(tables_by_jurisdiction=tables_by_jurisdiction)


@lru_cache(maxsize=1)
def load_default_child_support_registry() -> ChildSupportTableRegistry:
    default_data_dir = data_dir()
    return load_child_support_registry(
        default_data_dir / "child_support_lookup_2017.csv",
        default_data_dir / "child_support_over_150k_2017.csv",
    )


@lru_cache(maxsize=None)
def load_default_child_support_table(jurisdiction_code: str = "BC") -> ChildSupportTable:
    normalized_code = jurisdiction_code.upper()
    if normalized_code not in JURISDICTIONS_BY_CODE:
        raise ValueError(f"Unsupported jurisdiction code '{jurisdiction_code}'.")

    registry = load_default_child_support_registry()
    return registry.for_jurisdiction(normalized_code)
