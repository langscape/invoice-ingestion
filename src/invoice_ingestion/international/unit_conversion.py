"""Unit conversion for energy commodities."""
from __future__ import annotations

# Conversion factors
CONVERSIONS = {
    # Gas
    ("therms", "kWh"): 29.3071,
    ("kWh", "therms"): 1 / 29.3071,
    ("CCF", "therms"): 1.037,
    ("therms", "CCF"): 1 / 1.037,
    ("MCF", "therms"): 10.37,
    ("therms", "MCF"): 1 / 10.37,
    ("dekatherms", "therms"): 10.0,
    ("therms", "dekatherms"): 0.1,
    ("GJ", "kWh"): 277.778,
    ("kWh", "GJ"): 1 / 277.778,
    ("MWh", "kWh"): 1000.0,
    ("kWh", "MWh"): 0.001,
    ("CCF", "kWh"): 1.037 * 29.3071,
    ("kWh", "CCF"): 1 / (1.037 * 29.3071),
    # Water
    ("gallons", "m³"): 0.00378541,
    ("m³", "gallons"): 264.172,
    ("CCF_water", "gallons"): 748.0,
    ("gallons", "CCF_water"): 1 / 748.0,
    ("CCF_water", "m³"): 748.0 * 0.00378541,
    ("m³", "CCF_water"): 1 / (748.0 * 0.00378541),
}

# Canonical units per commodity and region
CANONICAL_UNITS = {
    ("electricity", "US"): "kWh",
    ("electricity", "EU"): "kWh",
    ("natural_gas", "US"): "therms",
    ("natural_gas", "EU"): "kWh",
    ("water", "US"): "gallons",
    ("water", "EU"): "m³",
}


def convert_units(value: float, from_unit: str, to_unit: str, calorific_value: float | None = None) -> float:
    """Convert between energy/volume units.

    For gas m³ → kWh conversion, calorific_value (kWh/m³) is required.
    """
    if from_unit == to_unit:
        return value

    # Special case: m³ to kWh for gas (requires calorific value)
    if from_unit == "m³" and to_unit == "kWh":
        if calorific_value is None:
            raise ValueError("Calorific value required for m³ → kWh conversion")
        return value * calorific_value

    if to_unit == "m³" and from_unit == "kWh":
        if calorific_value is None:
            raise ValueError("Calorific value required for kWh → m³ conversion")
        return value / calorific_value

    key = (from_unit, to_unit)
    if key in CONVERSIONS:
        return value * CONVERSIONS[key]

    raise ValueError(f"No conversion available from {from_unit} to {to_unit}")


def get_canonical_unit(commodity: str, region: str = "US") -> str:
    """Get the canonical unit for a commodity in a region."""
    return CANONICAL_UNITS.get((commodity, region), "kWh")


def normalize_unit_name(unit: str) -> str:
    """Normalize unit name to standard form."""
    mapping = {
        "kwh": "kWh", "kw": "kW", "mwh": "MWh", "mw": "MW",
        "therm": "therms", "thm": "therms",
        "ccf": "CCF", "mcf": "MCF",
        "dth": "dekatherms", "dekatherm": "dekatherms",
        "gj": "GJ",
        "m3": "m³", "m^3": "m³", "cbm": "m³", "cubic meters": "m³", "cubic metres": "m³",
        "gal": "gallons", "gallon": "gallons",
        "kva": "kVA", "kvar": "kVAR",
    }
    return mapping.get(unit.lower(), unit)
