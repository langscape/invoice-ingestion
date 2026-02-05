# Cross-Commodity Domain Knowledge

## Fixed Fees and Service Charges
Every utility bill includes **fixed charges** that do not vary with consumption. These are variously called:
- Service charge, customer charge, basic charge, meter charge, facility charge (US).
- Standing charge, Grundpreis, abonnement, quota fissa (EU).
- Fixed charges may be billed daily (e.g., p/day in UK) or monthly.
- Some tariffs have a "minimum bill" that is effectively a fixed charge floor.

## Taxes and Assessments
Utility bills include government-imposed taxes and fees:
- **Sales tax**: Applied to total charges in some US states (rates vary; some states exempt utilities).
- **Gross receipts tax / Utility tax**: A percentage tax on utility revenue, passed through to customers.
- **Franchise fee**: Fee paid by utility to the municipality, passed through as a line item.
- **Public purpose surcharge**: Funds energy efficiency, low-income assistance, renewable programs.
- **Regulatory assessment**: Fee to fund the state public utility commission.

## Late Fees and Penalties
- **Late payment charge**: Typically 1-1.5% per month on past-due balance.
- **Reconnection fee**: Charged when service is restored after disconnection for non-payment.
- **Returned payment fee**: For bounced checks or failed electronic payments.
- Late fees are applied to the **previous balance** if it was not paid by the due date.

## Budget Billing / Levelized Payment Plans
Customers may enroll in **budget billing** where monthly payments are levelized to a fixed amount based on estimated annual usage:
- The invoice still shows actual charges for the period.
- The "amount due" is the budget billing amount, not the actual charges.
- A running debit/credit balance tracks the difference between actual charges and budget payments.
- Periodically (usually annually), the budget amount is recalculated and the balance may be settled.
- Look for labels like "Budget Amount", "Levelized Billing", "Equal Payment Plan".

## Multi-Meter Accounts
Some invoices cover **multiple meters** at the same service address or across multiple addresses:
- Each meter has its own reads, consumption, and may have its own charges.
- Some charges (like a fixed customer charge) apply once per account, not per meter.
- Charges must be correctly attributed to the right meter.
- Some utilities consolidate all meters into a single total; others itemize per meter.

## Billing Determinants
**Billing determinants** are the quantities that drive charges: kWh, kW, therms, CCF, m3, number of days, etc. Each charge line typically has a quantity (billing determinant), a rate, and an amount. The fundamental equation is: **amount = quantity x rate**. When this equation does not hold, investigate rounding, minimum charges, or utility adjustments.

## Previous Balance / Payments / Adjustments
The financial summary section typically shows:
- **Previous balance**: Amount owed from the prior billing period.
- **Payment(s) received**: Customer payments applied since the last bill. Shown as negative or as a credit.
- **Late charges** (if applicable): Interest or penalties on unpaid balance.
- **Balance forward**: Previous balance - payments + late charges.
- **Current charges**: Total new charges for this billing period.
- **Total amount due**: Balance forward + current charges.

## Prior Period Adjustments
When a utility corrects a past billing error, the adjustment appears as a **prior period adjustment** on the current bill:
- Clearly labeled with the reference period being corrected.
- Can be positive (customer was underbilled) or negative (customer was overbilled).
- Must be flagged with attribution_type = "prior_period" in the extraction.

## Proration
Charges are **prorated** when:
- A rate change occurs mid-billing period (old rate for N days, new rate for M days).
- The customer moves in or out mid-period (partial month).
- Prorated charges show reduced quantities and amounts corresponding to the partial period.

## Minimum Bill
Some tariffs have a **minimum bill** or **minimum charge**:
- If actual charges fall below the minimum, the customer is billed the minimum amount.
- The invoice may show "Minimum Charge" or "Minimum Bill Adjustment" as a separate line.
- The math will not add up if you only look at line items -- the minimum replaces the sum.

## European VAT Structure

### Multiple VAT Rates
European utility invoices commonly apply **multiple VAT rates** to different components:
- **Standard rate** (e.g., 20% FR, 19% DE, 22% IT, 21% ES, 20% GB): Applied to most charges.
- **Reduced rate** (e.g., 5.5% FR, 7% DE for certain services, 10% IT): Applied to specific items like the standing charge, certain taxes, or water supply.
- Each charge line must be assigned the correct VAT rate and category.
- The VAT summary table at the bottom shows totals per rate.

### VAT Calculation Chain
The standard European invoice structure is:
1. **Net amount** (HT / Netto / Imponibile): Charge amount before VAT.
2. **VAT amount** (TVA / MwSt / IVA): Tax amount.
3. **Gross amount** (TTC / Brutto / Totale): Net + VAT.
- Verification: sum of all net amounts + sum of all VAT amounts = total gross (TTC).
- Each charge line should have net, VAT rate, VAT amount, and gross.

### Reverse Charge Mechanism
For B2B transactions across EU borders, the **reverse charge** mechanism may apply:
- The supplier does not charge VAT.
- The customer self-assesses and pays VAT directly to their tax authority.
- The invoice shows "Reverse Charge" or "Autoliquidation" and the total is net only.
- Both supplier and customer VAT numbers must be shown.

### Tax-on-Tax (Taxes Assises sur Taxes)
In some jurisdictions, certain taxes are included in the base for calculating other taxes:
- For example, in France, CTA is subject to 5.5% VAT, while CSPE/TICFE and TCFE are subject to 20% VAT.
- The energy tax may be part of the VAT base.
- This creates a "tax on tax" situation that must be understood for math validation.

### Energy Tax / Excise Duty (Accise / Energiesteuer / Impuesto)
Most European countries impose an **excise duty** on energy consumption:
- This is separate from VAT and is typically a fixed amount per kWh or per m3.
- It appears as a line item on the invoice.
- It IS included in the VAT base (the excise duty amount is subject to VAT).

### Eco-Taxes and Environmental Levies
- **CSPE/TICFE** (FR): French contribution to public electricity service.
- **Stromsteuer / Energiesteuer** (DE): German electricity/energy tax.
- **CCL** (GB): Climate Change Levy for business customers.
- **Impuesto electrico** (ES): Spanish electricity tax.
- **Accisa** (IT): Italian excise duty.
These are government-mandated charges, distinct from VAT, and typically appear in the taxes section of the invoice. They are always subject to VAT themselves.