"""Test gas calorific value conversion validation."""
import pytest
from invoice_ingestion.international.gas_conversion import validate_gas_conversion


class TestGasConversion:
    def test_valid_conversion(self):
        extraction = {"meters": [{
            "conversion_factors": {
                "calorific_value": {"value": 11.2, "unit": "kWh/m³"},
                "volume_correction_factor": {"value": 0.9626},
            },
            "consumption_volume": {"raw_value": 1250},
            "consumption_energy": {"raw_value": 13474.4},
        }]}
        result = validate_gas_conversion(extraction)
        assert result.passed

    def test_cv_out_of_range(self):
        extraction = {"meters": [{
            "conversion_factors": {
                "calorific_value": {"value": 5.0, "unit": "kWh/m³"},
            },
        }]}
        result = validate_gas_conversion(extraction)
        assert any("range" in i["message"].lower() for i in result.issues)

    def test_conversion_mismatch(self):
        extraction = {"meters": [{
            "conversion_factors": {
                "calorific_value": {"value": 11.2, "unit": "kWh/m³"},
                "volume_correction_factor": {"value": 0.9626},
            },
            "consumption_volume": {"raw_value": 1250},
            "consumption_energy": {"raw_value": 20000},  # Way off
        }]}
        result = validate_gas_conversion(extraction)
        assert not result.passed

    def test_missing_conversion_factors(self):
        extraction = {"meters": [{"consumption": {"raw_value": 1000}}]}
        result = validate_gas_conversion(extraction)
        assert result.passed  # No conversion to validate
