"""Country-specific charge taxonomies."""
from __future__ import annotations

CHARGE_TAXONOMIES: dict[str, dict[str, dict]] = {
    "DE": {
        "Arbeitspreis": {"category": "energy", "section": "supply", "translation": "Energy Charge (Working Price)"},
        "Grundpreis": {"category": "fixed", "section": "supply", "translation": "Standing Charge (Base Price)"},
        "Netzentgelt": {"category": "rider", "section": "distribution", "translation": "Network Charge"},
        "Messstellenbetrieb": {"category": "fixed", "section": "distribution", "translation": "Metering Operation"},
        "Stromsteuer": {"category": "tax", "section": "taxes", "translation": "Electricity Tax"},
        "EEG-Umlage": {"category": "rider", "section": "taxes", "translation": "Renewable Energy Levy"},
        "KWK-Umlage": {"category": "rider", "section": "taxes", "translation": "CHP Levy"},
        "Konzessionsabgabe": {"category": "rider", "section": "taxes", "translation": "Concession Fee"},
        "Offshore-Netzumlage": {"category": "rider", "section": "taxes", "translation": "Offshore Grid Levy"},
        "StromNEV-Umlage": {"category": "rider", "section": "taxes", "translation": "Grid Cost Levy"},
        "CO2-Abgabe": {"category": "tax", "section": "taxes", "translation": "CO2 Tax"},
        "Brennwert": {"category": "other", "section": "other", "translation": "Calorific Value"},
        "Zustandszahl": {"category": "other", "section": "other", "translation": "Volume Correction Factor"},
    },
    "FR": {
        "Abonnement": {"category": "fixed", "section": "supply", "translation": "Subscription Fee"},
        "Consommation": {"category": "energy", "section": "supply", "translation": "Energy Consumption"},
        "TURPE": {"category": "rider", "section": "distribution", "translation": "Grid Access Charge"},
        "CSPE": {"category": "rider", "section": "taxes", "translation": "Public Electricity Service Contribution"},
        "TCFE": {"category": "tax", "section": "taxes", "translation": "Final Electricity Consumption Tax"},
        "CTA": {"category": "rider", "section": "taxes", "translation": "Tariff Contribution"},
        "TVA": {"category": "tax", "section": "taxes", "translation": "VAT"},
        "Heures Pleines": {"category": "energy", "section": "supply", "translation": "Peak Hours"},
        "Heures Creuses": {"category": "energy", "section": "supply", "translation": "Off-Peak Hours"},
    },
    "ES": {
        "Energía activa": {"category": "energy", "section": "supply", "translation": "Active Energy"},
        "Potencia contratada": {"category": "demand", "section": "distribution", "translation": "Contracted Power"},
        "Potencia facturada": {"category": "demand", "section": "distribution", "translation": "Billed Power"},
        "Peaje de acceso": {"category": "rider", "section": "distribution", "translation": "Access Toll"},
        "Impuesto eléctrico": {"category": "tax", "section": "taxes", "translation": "Electricity Tax"},
        "IVA": {"category": "tax", "section": "taxes", "translation": "VAT"},
        "Alquiler contador": {"category": "fixed", "section": "distribution", "translation": "Meter Rental"},
    },
    "UK": {
        "Unit Rate": {"category": "energy", "section": "supply", "translation": "Unit Rate"},
        "Standing Charge": {"category": "fixed", "section": "supply", "translation": "Standing Charge"},
        "CCL": {"category": "tax", "section": "taxes", "translation": "Climate Change Levy"},
        "DUoS": {"category": "rider", "section": "distribution", "translation": "Distribution Use of System"},
        "TNUoS": {"category": "rider", "section": "distribution", "translation": "Transmission Use of System"},
        "BSUoS": {"category": "rider", "section": "distribution", "translation": "Balancing Services Use of System"},
        "Capacity Market": {"category": "rider", "section": "distribution", "translation": "Capacity Market Charge"},
        "FiT": {"category": "credit", "section": "supply", "translation": "Feed-in Tariff"},
        "RO": {"category": "rider", "section": "taxes", "translation": "Renewables Obligation"},
        "VAT": {"category": "tax", "section": "taxes", "translation": "Value Added Tax"},
    },
    "IT": {
        "Energia": {"category": "energy", "section": "supply", "translation": "Energy"},
        "Trasporto e gestione del contatore": {"category": "rider", "section": "distribution", "translation": "Transport and Meter Management"},
        "Oneri di sistema": {"category": "rider", "section": "taxes", "translation": "System Charges"},
        "Accisa": {"category": "tax", "section": "taxes", "translation": "Excise Duty"},
        "IVA": {"category": "tax", "section": "taxes", "translation": "VAT"},
        "Canone RAI": {"category": "rider", "section": "taxes", "translation": "TV License Fee"},
    },
    "NL": {
        "Leveringskosten": {"category": "energy", "section": "supply", "translation": "Supply Costs"},
        "Vastrecht": {"category": "fixed", "section": "supply", "translation": "Standing Charge"},
        "Transportkosten": {"category": "rider", "section": "distribution", "translation": "Transport Costs"},
        "Energiebelasting": {"category": "tax", "section": "taxes", "translation": "Energy Tax"},
        "ODE": {"category": "tax", "section": "taxes", "translation": "Renewable Energy Surcharge (ODE)"},
        "BTW": {"category": "tax", "section": "taxes", "translation": "VAT"},
        "Belastingvermindering": {"category": "credit", "section": "taxes", "translation": "Tax Reduction"},
    },
    "MX": {
        "Energía": {"category": "energy", "section": "supply", "translation": "Energy"},
        "Demanda": {"category": "demand", "section": "supply", "translation": "Demand"},
        "Distribución": {"category": "rider", "section": "distribution", "translation": "Distribution"},
        "Capacidad": {"category": "demand", "section": "distribution", "translation": "Capacity"},
        "DAP": {"category": "rider", "section": "taxes", "translation": "Public Lighting Charge"},
        "IVA": {"category": "tax", "section": "taxes", "translation": "VAT (IVA)"},
        "Factor de potencia": {"category": "penalty", "section": "other", "translation": "Power Factor"},
        "Suministro": {"category": "fixed", "section": "supply", "translation": "Supply Fee"},
    },
}


def lookup_charge(country_code: str, description: str) -> dict | None:
    """Look up a charge description in the country taxonomy.
    Returns matching taxonomy entry or None.
    """
    taxonomy = CHARGE_TAXONOMIES.get(country_code, {})
    desc_lower = description.lower()

    for key, info in taxonomy.items():
        if key.lower() in desc_lower:
            return info

    return None


def get_taxonomy(country_code: str) -> dict[str, dict]:
    """Get the full charge taxonomy for a country."""
    return CHARGE_TAXONOMIES.get(country_code, {})
