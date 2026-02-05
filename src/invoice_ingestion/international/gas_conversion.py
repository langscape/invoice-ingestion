"""Gas calorific value conversion validation."""
from __future__ import annotations

class GasConversionResult:
    def __init__(self):
        self.issues: list[dict] = []
        self.passed: bool = True

    def add_issue(self, severity: str, message: str, expected: float | None = None, actual: float | None = None):
        self.issues.append({"severity": severity, "message": message, "expected": expected, "actual": actual})
        if severity == "error":
            self.passed = False


# Reasonable ranges for calorific values
CV_RANGE_KWH_M3 = (8.0, 14.0)  # kWh/m³, typical range for natural gas
CV_RANGE_BTU_CF = (900, 1200)    # BTU/cf, typical range


def validate_gas_conversion(extraction: dict, tolerance_pct: float = 0.02) -> GasConversionResult:
    """Validate gas volume → energy conversion.

    Formula: volume (m³) × VCF × CV (kWh/m³) = energy (kWh)

    Checks:
    1. If conversion_factors present, validate the formula
    2. CV within reasonable range
    3. VCF within reasonable range (0.9 - 1.1)
    """
    result = GasConversionResult()
    meters = extraction.get("meters", [])

    for meter in meters:
        conversion = meter.get("conversion_factors")
        if not conversion:
            continue

        cv_field = conversion.get("calorific_value")
        vcf_field = conversion.get("volume_correction_factor")

        cv = _get_value(cv_field) if cv_field else None
        vcf = _get_value(vcf_field) if vcf_field else 1.0

        # Check CV range
        if cv is not None:
            cv_unit = cv_field.get("unit", "kWh/m³") if isinstance(cv_field, dict) else "kWh/m³"
            if "kWh" in cv_unit:
                if cv < CV_RANGE_KWH_M3[0] or cv > CV_RANGE_KWH_M3[1]:
                    result.add_issue("warning",
                                    f"Calorific value {cv} {cv_unit} outside expected range {CV_RANGE_KWH_M3}",
                                    expected=None, actual=cv)

        # Check VCF range
        if vcf is not None and vcf != 1.0:
            if vcf < 0.9 or vcf > 1.1:
                result.add_issue("warning",
                                f"Volume correction factor {vcf} outside expected range (0.9-1.1)",
                                expected=None, actual=vcf)

        # Validate conversion formula
        consumption_volume = meter.get("consumption_volume") or meter.get("consumption")
        consumption_energy = meter.get("consumption_energy")

        if consumption_volume and consumption_energy and cv is not None:
            volume = _get_raw_value(consumption_volume)
            energy = _get_raw_value(consumption_energy)

            if volume is not None and energy is not None:
                expected_energy = volume * (vcf or 1.0) * cv
                variance_pct = abs(expected_energy - energy) / energy if energy != 0 else float('inf')

                if variance_pct > tolerance_pct:
                    result.add_issue("error",
                                    f"Gas conversion mismatch: {volume} × {vcf} × {cv} = {expected_energy:.1f}, stated {energy}",
                                    expected=round(expected_energy, 1), actual=energy)

    return result


def _get_value(field) -> float | None:
    if field is None:
        return None
    if isinstance(field, (int, float)):
        return float(field)
    if isinstance(field, dict):
        return field.get("value")
    return None


def _get_raw_value(consumption) -> float | None:
    if isinstance(consumption, dict):
        return consumption.get("raw_value") or consumption.get("value")
    return None
