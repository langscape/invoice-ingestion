# Natural Gas Domain Knowledge

## Commodity vs Delivery (US Deregulated Markets)
Natural gas invoices in deregulated markets split into two major sections: **commodity** (the gas itself, purchased from a supplier/marketer) and **delivery** (transportation and distribution, charged by the local utility/LDC). The commodity charge is based on volume consumed (therms, CCF, MCF, or dekatherms). The delivery charge covers bringing gas through the pipeline system to the customer's meter. Some invoices show both on one bill (consolidated billing), others arrive as two separate bills.

## Volume Units and Conversions
- **CCF** = 100 cubic feet (Centum Cubic Feet). The most common raw meter unit in the US.
- **MCF** = 1,000 cubic feet (Mille Cubic Feet). Used for larger commercial accounts.
- **Therms** = 100,000 BTU. The standard billing unit in many US states. One CCF is approximately 1.0 therms depending on BTU content.
- **Dekatherms (Dth)** = 10 therms = 1,000,000 BTU. Common in wholesale and large commercial.
- **GJ (Gigajoule)** = 9.4804 therms. Used in Canada.
- The conversion from CCF to therms uses a **BTU factor** (also called therm factor or heating value), typically between 0.95 and 1.10, printed on the invoice. If not shown, assume 1.0 and flag low confidence.

## Demand Charges for Gas
Large commercial/industrial gas customers may have **demand charges** based on peak daily or hourly gas usage (in MCF/day, therms/day, or Dth/day). This is separate from the volumetric commodity charge.

## Balancing and Adjustment Charges
- **Gas Cost Adjustment (GCA)** / **Purchased Gas Adjustment (PGA)**: A per-therm adjustment that tracks the difference between the gas cost embedded in base rates and the actual market cost. Can be positive or negative.
- **Balancing charges**: In transportation programs, charges for imbalances between nominated and actual gas usage.
- **Weather normalization adjustment (WNA)**: Adjusts bills to remove the effect of unusually warm or cold weather, based on Heating Degree Days (HDD). Not all utilities use WNA.

## Minimum Bill / Take-or-Pay
Some gas tariffs have a **minimum bill** provision, especially for large customers with contracted capacity. If actual usage falls below a threshold, the customer is billed the minimum amount. This appears as a "minimum charge" or "take-or-pay" charge.

## Transportation Tiers
Large customers may be on **gas transportation** tariffs (as opposed to bundled sales service). Transportation customers buy gas from a third-party supplier and pay the utility only for delivery. Transportation tariffs may have tiered delivery rates based on annual volume commitments.

## Capacity Assignment
In some states, transportation customers are assigned a share of **pipeline capacity** and pay capacity reservation charges. These are fixed charges based on maximum daily quantity (MDQ) commitments.

## Heating Degree Days (HDD)
HDD = max(0, 65 - average_daily_temperature). Shown on some invoices for context. A 30-day billing period might show "HDD: 450" meaning it was cold. Used in weather normalization and consumption comparison to prior year.

## European Gas Concepts

### Calorific Value (PCS / PCI / Brennwert / Ho / Hu)
European gas is metered in **cubic meters (m3)** at the meter but billed in **kWh**. The conversion uses the **calorific value** (energy content per unit volume):
- **PCS** (Pouvoir Calorifique Superieur) / **Ho** / **Brennwert**: Gross/superior calorific value. Typical range: 10.0-12.5 kWh/m3.
- **PCI** (Pouvoir Calorifique Inferieur) / **Hu** / **Heizwert**: Net/inferior calorific value. Typically ~90% of PCS.
- Most European countries bill on PCS/Brennwert (gross). The value is printed on the invoice or in a reference table.

### Volume Correction Factor (VCF / Zustandszahl / Coefficient de Conversion)
The VCF (also called Z-Zahl in Germany or coefficient de conversion in France) adjusts raw meter volume to standard conditions (temperature, pressure, compressibility). Typical range: 0.9-1.1. The conversion formula is: **kWh = m3 x VCF x Calorific Value**.

### Gas Billed in kWh
After conversion, European gas consumption is expressed in kWh, and all charges (commodity, network) are priced in EUR/kWh (or ct/kWh, p/kWh). This is fundamentally different from US gas billing in therms or CCF.

### Standing Charge (Grundpreis / Abonnement)
A fixed periodic charge for maintaining the gas connection, independent of consumption. May be monthly, quarterly, or annual. In Germany, this is the "Grundpreis" (base price). In France, "Abonnement".

### European Gas Levies and Taxes
- **Energiesteuer** (DE): German energy tax on gas, per kWh.
- **CO2-Abgabe / CO2-Preis** (DE): Carbon price levy on gas.
- **TICGN** (FR): French domestic tax on natural gas consumption.
- **CTA** (FR): Contribution to the pension fund for gas/electricity workers.
- **Accisa** (IT): Italian excise duty on gas, varies by consumption bracket.
- **Addizionale regionale** (IT): Italian regional surcharge on gas.