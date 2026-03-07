import csv
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

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
    lookup_by_children: dict[int, dict[int, float]]
    over_150k_rules: dict[int, Over150kRule]

    def available_children(self) -> list[int]:
        return sorted(self.lookup_by_children)

    def normalized_children(self, num_children: int) -> int:
        if num_children not in self.lookup_by_children:
            raise ValueError(f"No support rules were found for {num_children} children.")
        return num_children

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
                "Child support lookup hit simplified table: children=%s income=%s rounded=%s amount=%s",
                normalized_children,
                income,
                rounded_income,
                amount,
            )
            return round(amount, 2)

        if income < MIN_CHILD_SUPPORT_INCOME:
            logger.debug("Income %s falls below the simplified table minimum.", income)
            return 0.0

        rule = self.over_150k_rules[normalized_children]
        amount = rule.base_amount + (income - rule.income_over) * rule.plus_pct / 100.0
        logger.debug(
            "Child support calculated from over-150k rule: children=%s income=%s amount=%s",
            normalized_children,
            income,
            amount,
        )
        return round(max(amount, 0.0), 2)


def load_child_support_table(csv_path: Path) -> ChildSupportTable:
    logger.info("Loading child support lookup table from %s", csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Support table not found at {csv_path}")

    lookup_by_children: dict[int, dict[int, float]] = {}
    with csv_path.open(newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            children = int(row["Children"])
            income = int(row["Income"])
            amount = float(row["Amount"])
            lookup_by_children.setdefault(children, {})[income] = amount

    over_150k_rules = {
        1: Over150kRule(base_amount=1356.0, plus_pct=0.78),
        2: Over150kRule(base_amount=2159.0, plus_pct=1.18),
        3: Over150kRule(base_amount=2802.0, plus_pct=1.56),
        4: Over150kRule(base_amount=3328.0, plus_pct=1.88),
        5: Over150kRule(base_amount=3766.0, plus_pct=2.10),
        6: Over150kRule(base_amount=4137.0, plus_pct=2.32),
        7: Over150kRule(base_amount=4137.0, plus_pct=2.32),
    }

    logger.info("Loaded child support data for child counts: %s", sorted(lookup_by_children))
    return ChildSupportTable(
        lookup_by_children=lookup_by_children,
        over_150k_rules=over_150k_rules,
    )


@lru_cache(maxsize=1)
def load_default_child_support_table() -> ChildSupportTable:
    csv_path = Path(__file__).resolve().parent / "data" / "bc_child_support_lookup_2017.csv"
    return load_child_support_table(csv_path)
