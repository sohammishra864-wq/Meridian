from enum import Enum
from dataclasses import dataclass
from typing import Callable


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationRule:
    name: str
    severity: ValidationSeverity
    description: str
    check: Callable[[dict], bool]


XBRL_VALIDATION_RULES = [
    # ERROR: blocks storage
    ValidationRule(
        "revenue_positive",
        ValidationSeverity.ERROR,
        "Revenue must be positive",
        lambda f: f.get("Revenue", 0) > 0
    ),
    ValidationRule(
        "assets_positive",
        ValidationSeverity.ERROR,
        "Total Assets must be positive",
        lambda f: f.get("Assets", 0) > 0
    ),
    ValidationRule(
        "cash_non_negative",
        ValidationSeverity.ERROR,
        "Cash cannot be negative",
        lambda f: f.get("CashAndCashEquivalents", 0) >= 0
    ),
    ValidationRule(
        "shares_positive",
        ValidationSeverity.ERROR,
        "Shares outstanding must be positive",
        lambda f: f.get("CommonStockSharesOutstanding", 0) > 0
    ),
    # WARNING: stores with confidence penalty
    ValidationRule(
        "assets_gte_liabilities",
        ValidationSeverity.WARNING,
        "Assets should be >= Liabilities",
        lambda f: f.get("Assets", 0) >= f.get("Liabilities", 0)
    ),
    ValidationRule(
        "gross_profit_lte_revenue",
        ValidationSeverity.WARNING,
        "Gross Profit should not exceed Revenue",
        lambda f: f.get("GrossProfit", 0) <= f.get("Revenue", 1)
    ),
    ValidationRule(
        "capex_non_negative",
        ValidationSeverity.WARNING,
        "CapEx should be non-negative",
        lambda f: abs(f.get("PaymentsToAcquirePropertyPlantAndEquipment", 0)) >= 0
    ),
    ValidationRule(
        "ocf_reasonableness",
        ValidationSeverity.WARNING,
        "Operating cash flow within 2x revenue",
        lambda f: abs(f.get("NetCashProvidedByUsedInOperatingActivities", 0)) <= f.get("Revenue", float("inf")) * 2
    ),
]


def validate_xbrl_facts(facts: dict) -> tuple[bool, list[str], float]:
    """
    Returns: (is_valid, error_messages, confidence_multiplier)
    """
    errors, warnings = [], []

    for rule in XBRL_VALIDATION_RULES:
        try:
            passed = rule.check(facts)
        except (KeyError, ZeroDivisionError, TypeError):
            passed = False

        if not passed:
            msg = f"[{rule.severity.value.upper()}] {rule.name}: {rule.description}"
            if rule.severity == ValidationSeverity.ERROR:
                errors.append(msg)
            else:
                warnings.append(msg)

    is_valid = len(errors) == 0
    confidence_multiplier = max(1.0 - (0.05 * len(warnings)), 0.5)
    return is_valid, errors + warnings, confidence_multiplier
