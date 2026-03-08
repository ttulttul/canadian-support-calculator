import csv
import logging
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

from support_calculator.jurisdictions import NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "support_calculator" / "data"
LOOKUP_OUTPUT_PATH = OUTPUT_DIR / "child_support_lookup_2017.csv"
OVER_150K_OUTPUT_PATH = OUTPUT_DIR / "child_support_over_150k_2017.csv"
ARCHIVED_SECTION_URL = (
    "https://laws.justice.gc.ca/eng/regulations/SOR-97-175/"
    "section-sched{section_id}-20171122.html?wbdisable=true"
)

CHILD_COUNT_LABELS = {
    "One/Un": 1,
    "Two/Deux": 2,
    "Three/Trois": 3,
    "Four/Quatre": 4,
    "Five/Cinq": 5,
    "Six or more/Six ou plus": 6,
}


@dataclass(frozen=True)
class SimplifiedTableRule:
    income_from: int
    income_to: int | None
    basic_amount: float
    plus_pct: float
    income_over: int


class JusticeScheduleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.tables: list[list[list[str]]] = []
        self.current_table: list[list[str]] = []
        self.current_row: list[str] = []
        self.current_cell_data: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self.in_table = True
            self.current_table = []
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ("th", "td") and self.in_row:
            self.in_cell = True
            self.current_cell_data = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("th", "td") and self.in_cell:
            cell_text = " ".join("".join(self.current_cell_data).split())
            self.current_row.append(cell_text)
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.current_table.append(self.current_row)
            self.in_row = False
        elif tag == "table" and self.in_table:
            self.tables.append(self.current_table)
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell_data.append(data)


def _child_count_for_table(table_rows: list[list[str]]) -> int:
    for row in table_rows[:4]:
        row_text = " ".join(row).replace(" /", "/").replace("/ ", "/")
        for label, count in CHILD_COUNT_LABELS.items():
            if label in row_text:
                return count

    raise ValueError("Unable to determine child count from Justice schedule table.")


def _parse_income_to(value: str) -> int | None:
    normalized_value = value.strip().lower()
    if "or greater" in normalized_value or "ou plus" in normalized_value:
        return None
    return int(normalized_value)


def _extract_rules(table_rows: list[list[str]]) -> list[SimplifiedTableRule]:
    rules: list[SimplifiedTableRule] = []
    for row in table_rows:
        if not row:
            continue

        for offset in range(0, len(row), 5):
            group = row[offset : offset + 5]
            if len(group) < 5 or not group[0].isdigit():
                continue

            rules.append(
                SimplifiedTableRule(
                    income_from=int(group[0]),
                    income_to=_parse_income_to(group[1]),
                    basic_amount=float(group[2]),
                    plus_pct=float(group[3]),
                    income_over=int(group[4]),
                )
            )

    if not rules:
        raise ValueError("No child-support rules could be extracted from Justice schedule table.")

    return rules


def _amount_for_income(rules: list[SimplifiedTableRule], income: int) -> float:
    for rule in rules:
        if rule.income_to is None:
            if income >= rule.income_from:
                return float(
                    round(
                        rule.basic_amount
                        + (income - rule.income_over) * rule.plus_pct / 100.0
                    )
                )
            continue

        if rule.income_from <= income <= rule.income_to:
            return float(
                round(
                    rule.basic_amount
                    + (income - rule.income_over) * rule.plus_pct / 100.0
                )
            )

    raise ValueError(f"No matching child-support rule found for income {income}.")


def _fetch_jurisdiction_tables(section_id: int) -> list[list[list[str]]]:
    url = ARCHIVED_SECTION_URL.format(section_id=section_id)
    logger.info("Fetching archived Justice schedule %s", url)
    with urlopen(url, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")

    parser = JusticeScheduleParser()
    parser.feed(html)
    if not parser.tables:
        raise ValueError(f"No tables were parsed from {url}")

    logger.info("Parsed %s schedule tables from %s", len(parser.tables), url)
    return parser.tables


def generate_child_support_csvs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lookup_rows: list[dict[str, str | int | float]] = []
    over_150k_rows: list[dict[str, str | int | float]] = []

    for jurisdiction in NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS:
        if jurisdiction.child_support_section_id is None:
            raise ValueError(
                f"No archived child-support source was configured for {jurisdiction.code}."
            )

        tables = _fetch_jurisdiction_tables(jurisdiction.child_support_section_id)
        if len(tables) != 6:
            raise ValueError(
                f"Expected 6 child-count tables for {jurisdiction.code}, found {len(tables)}."
            )

        rules_by_children: dict[int, list[SimplifiedTableRule]] = {}
        for table in tables:
            child_count = _child_count_for_table(table)
            rules = _extract_rules(table)
            rules_by_children[child_count] = rules

        for child_count, rules in sorted(rules_by_children.items()):
            over_150k_rule = next(rule for rule in rules if rule.income_to is None)
            over_150k_rows.append(
                {
                    "Jurisdiction": jurisdiction.code,
                    "Children": child_count,
                    "BasicAmount": over_150k_rule.basic_amount,
                    "PlusPct": over_150k_rule.plus_pct,
                    "OfIncomeOver": over_150k_rule.income_over,
                }
            )
            for income in range(12_000, 150_001, 100):
                lookup_rows.append(
                    {
                        "Jurisdiction": jurisdiction.code,
                        "Children": child_count,
                        "Income": income,
                        "Amount": _amount_for_income(rules, income),
                    }
                )

            if child_count == 6:
                duplicate_lookup_rows = [
                    {
                        **row,
                        "Children": 7,
                    }
                    for row in lookup_rows
                    if row["Jurisdiction"] == jurisdiction.code and row["Children"] == 6
                ]
                lookup_rows.extend(duplicate_lookup_rows)
                over_150k_rows.append(
                    {
                        "Jurisdiction": jurisdiction.code,
                        "Children": 7,
                        "BasicAmount": over_150k_rule.basic_amount,
                        "PlusPct": over_150k_rule.plus_pct,
                        "OfIncomeOver": over_150k_rule.income_over,
                    }
                )

    logger.info("Writing %s", LOOKUP_OUTPUT_PATH)
    with LOOKUP_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["Jurisdiction", "Children", "Income", "Amount"],
        )
        writer.writeheader()
        writer.writerows(
            sorted(
                lookup_rows,
                key=lambda row: (
                    row["Jurisdiction"],
                    int(row["Children"]),
                    int(row["Income"]),
                ),
            )
        )

    logger.info("Writing %s", OVER_150K_OUTPUT_PATH)
    with OVER_150K_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "Jurisdiction",
                "Children",
                "BasicAmount",
                "PlusPct",
                "OfIncomeOver",
            ],
        )
        writer.writeheader()
        writer.writerows(
            sorted(
                over_150k_rows,
                key=lambda row: (row["Jurisdiction"], int(row["Children"])),
            )
        )

    logger.info(
        "Generated child-support CSVs for %s jurisdictions.",
        len(NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS),
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    generate_child_support_csvs()


if __name__ == "__main__":
    main()
