# Electricity Domain Knowledge

## Supply vs Distribution (Deregulated Markets)
In deregulated electricity markets, the invoice separates **supply** (generation, purchased from a competitive supplier at a negotiated rate) from **distribution** (delivery, charged by the local utility at regulated rates). In regulated markets, the utility provides both and the invoice may not split them, though charges are still categorized by function (generation, transmission, distribution).

## Demand Charges
Commercial and industrial customers typically have a **demand charge** based on their peak power draw during the billing period, measured in **kW** (kilowatts) or **kVA** (kilovolt-amperes).
- **Billing demand** may be the highest 15-minute average demand in the billing period.
- Some tariffs use a **ratchet**: billing demand is the maximum of current month demand or a percentage (often 80%) of the highest demand in the prior 11 months.
- Demand charges can be significant -- often 30-50% of a large customer's total bill.

## Time-of-Use (TOU) Rates
TOU pricing varies the per-kWh rate by time of day and season:
- **On-Peak**: Highest price, typically weekday afternoons (e.g., 12pm-6pm summer).
- **Off-Peak**: Lowest price, typically nights and weekends.
- **Shoulder / Mid-Peak / Partial Peak**: Intermediate pricing.
- Some tariffs also have **TOU demand charges** (separate on-peak and off-peak demand).
- The invoice shows consumption (kWh) and sometimes demand (kW) broken down by TOU period.

## Net Metering
Customers with solar panels or other generation may have **net metering**:
- The meter runs both ways, measuring consumption and generation/export.
- The invoice shows **generation** (kWh exported) as a credit.
- **Net consumption** = total consumption - generation.
- Excess generation may roll over as a credit to the next billing period.

## Power Factor Penalties
Power factor measures how efficiently electrical power is used. Industrial customers with poor power factor (below 0.85 or 0.90) may incur a **power factor penalty** or **reactive power charge**. Billed in kVAR (reactive kilovolt-amperes) or as a percentage surcharge on demand charges.

## Capacity and Transmission Tags
- **ICAP** (Installed Capacity): A capacity tag based on the customer's contribution to system peak demand. Used to allocate capacity costs.
- **PLC** (Peak Load Contribution): Similar to ICAP, used in PJM and other ISOs. The customer's demand at the time of system peak.
- **NSPL** (Network Service Peak Load): Transmission cost allocation tag.
- These tags are fixed for a planning year and shown on the invoice for reference.

## Riders and Surcharges
Electricity invoices frequently include numerous riders, surcharges, and adjustments:
- **Fuel adjustment / Energy cost adjustment**: Tracks actual fuel costs vs embedded base rate.
- **Renewable energy surcharge**: Funds renewable energy programs.
- **System benefits charge**: Funds energy efficiency, low-income assistance.
- **Transmission charge**: Per-kWh charge for high-voltage transmission.
- **Transition charge / CTC**: Cost recovery for stranded generation assets during deregulation.
- **Revenue decoupling adjustment**: Adjusts for actual vs forecasted sales.

## Rate Schedule / Tariff Code
Every customer is assigned a **rate schedule** (e.g., "SC-1", "GS-2", "TOU-8", "Rate B"). This determines the pricing structure. The rate schedule name appears on the invoice and is important for charge validation.

## Coincident vs Non-Coincident Demand
- **Non-coincident demand (NCD)**: The customer's peak demand regardless of when it occurs.
- **Coincident demand (CD)**: The customer's demand at the time of the system peak (or a predefined coincident peak window). Usually lower than NCD.
- Some tariffs bill both, or bill distribution on NCD and transmission on CD.

## Reactive Demand
- **Reactive demand** (kVAR): Some tariffs separately bill reactive power demand.
- **Apparent demand** (kVA): Some tariffs bill on kVA (which incorporates power factor) instead of kW.

## European Electricity Concepts

### Network / Grid Charges
European electricity invoices separate **energy** (commodity, from the supplier) from **network** charges (from the DSO/grid operator). Network charges typically include:
- **Energy-based network fee**: Per-kWh charge for grid usage.
- **Capacity-based network fee**: Per-kW charge based on contracted or metered capacity.
- **Metering fee (Messentgelt / Messstellenbetrieb)**: For meter operation and reading.
- **Concession fee (Konzessionsabgabe)**: Fee paid to the municipality for use of public rights-of-way.

### Energy Taxes and Levies
- **Stromsteuer** (DE): German electricity tax, fixed per kWh.
- **EEG-Umlage** (DE): Renewable energy surcharge (historically large, reduced/eliminated in 2022-2023 but may appear on older invoices).
- **KWK-Aufschlag** (DE): Combined heat and power surcharge.
- **Offshore-Netzumlage** (DE): Offshore wind grid surcharge.
- **CSPE / TICFE** (FR): French contribution to public electricity service / domestic tax on final electricity consumption.
- **TCFE** (FR): Local taxes on final electricity consumption (communale + departementale).
- **Accisa** (IT): Italian excise duty on electricity.
- **Impuesto electrico** (ES): Spanish electricity tax (5.11% of base).
- **Climate Change Levy / CCL** (GB): UK tax on energy used by businesses.

### Contracted Power (Puissance Souscrite / Potenza Impegnata / Leistung)
European customers subscribe to a **contracted power** level (in kW or kVA). This determines:
- The fixed/capacity component of network charges.
- Penalty charges if actual demand exceeds contracted power (depassement / superamento potenza).
- The contracted power level is printed on the invoice and is critical for charge validation.

### Time Periods by Country
- **France**: HP/HC (Heures Pleines / Heures Creuses) or Tempo (Bleu/Blanc/Rouge x HP/HC).
- **Italy**: F1/F2/F3 (fascia oraria: peak, mid-peak, off-peak).
- **Spain**: P1-P6 (six time periods for larger customers).
- **Germany**: HT/NT (Hochtarif / Niedertarif) for older tariffs, or specific time windows.
- **UK**: Day/Night, or Economy 7/10 for domestic TOU tariffs.

### Green Certificates / Guarantees of Origin
Some invoices show charges or credits related to green energy certificates (Herkunftsnachweise, Garanties d'Origine, GO). These certify the renewable origin of electricity.

### Feed-in Tariff
Customers with generation (solar, wind) may receive **feed-in tariff** payments for exported electricity. On the invoice, this appears as a credit or as a separate settlement.