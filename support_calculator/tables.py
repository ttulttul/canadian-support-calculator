import csv
import logging
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupportRule:
    lower: float
    upper: float | None
    basic_amount: float
    plus_pct: float
    income_over: float


@dataclass(frozen=True)
class ChildSupportTable:
    rules_by_children: dict[int, tuple[SupportRule, ...]]
    lower_bounds_by_children: dict[int, tuple[float, ...]]

    def available_children(self) -> list[int]:
        return sorted(self.rules_by_children)

    def amount(self, num_children: int, income: float) -> float:
        if income < 0:
            raise ValueError("Income must be zero or greater.")

        if num_children not in self.rules_by_children:
            raise ValueError(f"No support rules were found for {num_children} children.")

        lower_bounds = self.lower_bounds_by_children[num_children]
        index = bisect_right(lower_bounds, income) - 1
        if index < 0:
            logger.debug("Income %s falls below the table minimum.", income)
            return 0.0

        rule = self.rules_by_children[num_children][index]
        if rule.upper is not None and income > rule.upper:
            logger.debug("Income %s falls above the selected bracket upper bound.", income)
            return 0.0

        amount = rule.basic_amount + (income - rule.income_over) * rule.plus_pct / 100.0
        return round(max(amount, 0.0), 2)


def load_child_support_table(csv_path: Path) -> ChildSupportTable:
    logger.info("Loading child support table from %s", csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Support table not found at {csv_path}")

    rules_by_children: dict[int, list[SupportRule]] = {}
    with csv_path.open(newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            children = int(row["Children"])
            upper_raw = row["To"].strip()
            upper = None if upper_raw == "or greater" else float(upper_raw)
            rule = SupportRule(
                lower=float(row["From"]),
                upper=upper,
                basic_amount=float(row["Basic Amount"]),
                plus_pct=float(row["Plus\n(%)"]),
                income_over=float(row["Of Income Over"]),
            )
            rules_by_children.setdefault(children, []).append(rule)

    frozen_rules = {
        children: tuple(sorted(rules, key=lambda rule: rule.lower))
        for children, rules in rules_by_children.items()
    }
    lower_bounds = {
        children: tuple(rule.lower for rule in rules)
        for children, rules in frozen_rules.items()
    }

    logger.info("Loaded child support table for child counts: %s", sorted(frozen_rules))
    return ChildSupportTable(
        rules_by_children=frozen_rules,
        lower_bounds_by_children=lower_bounds,
    )


@lru_cache(maxsize=1)
def load_default_child_support_table() -> ChildSupportTable:
    csv_path = Path(__file__).resolve().parent / "data" / "bc_child_support_tables_2017.csv"
    return load_child_support_table(csv_path)
