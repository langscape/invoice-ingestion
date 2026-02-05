"""Test unit conversions."""
import pytest
from invoice_ingestion.international.unit_conversion import convert_units, normalize_unit_name, get_canonical_unit


class TestConvertUnits:
    def test_therms_to_kwh(self):
        result = convert_units(1.0, "therms", "kWh")
        assert abs(result - 29.3071) < 0.01

    def test_kwh_to_therms(self):
        result = convert_units(29.3071, "kWh", "therms")
        assert abs(result - 1.0) < 0.01

    def test_ccf_to_therms(self):
        result = convert_units(1.0, "CCF", "therms")
        assert abs(result - 1.037) < 0.01

    def test_mwh_to_kwh(self):
        assert convert_units(1.0, "MWh", "kWh") == 1000.0

    def test_gallons_to_m3(self):
        result = convert_units(264.172, "gallons", "m³")
        assert abs(result - 1.0) < 0.01

    def test_m3_to_gallons(self):
        result = convert_units(1.0, "m³", "gallons")
        assert abs(result - 264.172) < 0.01

    def test_same_unit(self):
        assert convert_units(42.0, "kWh", "kWh") == 42.0

    def test_m3_to_kwh_requires_cv(self):
        with pytest.raises(ValueError, match="[Cc]alorific"):
            convert_units(100, "m³", "kWh")

    def test_m3_to_kwh_with_cv(self):
        result = convert_units(100, "m³", "kWh", calorific_value=11.2)
        assert abs(result - 1120.0) < 0.1

    def test_unknown_conversion(self):
        with pytest.raises(ValueError):
            convert_units(1.0, "apples", "oranges")


class TestNormalizeUnitName:
    def test_kwh(self):
        assert normalize_unit_name("kwh") == "kWh"

    def test_m3_variants(self):
        assert normalize_unit_name("m3") == "m³"
        assert normalize_unit_name("m^3") == "m³"
        assert normalize_unit_name("cbm") == "m³"

    def test_therm(self):
        assert normalize_unit_name("therm") == "therms"


class TestGetCanonicalUnit:
    def test_us_gas(self):
        assert get_canonical_unit("natural_gas", "US") == "therms"

    def test_eu_gas(self):
        assert get_canonical_unit("natural_gas", "EU") == "kWh"

    def test_us_electric(self):
        assert get_canonical_unit("electricity", "US") == "kWh"
