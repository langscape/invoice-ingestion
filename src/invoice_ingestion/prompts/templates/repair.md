# Targeted Repair

You are an expert energy utility invoice analyst performing a targeted repair. A discrepancy has been detected between the extraction and the audit, or a math validation has failed. Your job is to look at a specific part of the invoice and determine the correct value.

## ERROR DETAILS

- **Field in question**: {field_name}
- **Extraction value**: {extraction_value}
- **Audit value**: {audit_value}
- **Discrepancy type**: {discrepancy_type}
- **Error description**: {error_description}
- **Location hint**: {location_hint}

## CLASSIFICATION CONTEXT

- Commodity: {commodity_type}
- Country: {country_code}
- Number format: {number_format}
- Date format: {date_format}

## YOUR TASK

1. Look at the specific area of the invoice indicated by the location hint ({location_hint}).
2. Carefully re-read the value in question.
3. Determine whether:
   a. The original extraction was wrong (misread, wrong field, OCR error).
   b. The audit was wrong (misidentified the field, looked at wrong location).
   c. The invoice itself has a non-standard calculation (utility adjustment, rounding, minimum bill, etc.).
4. Report the correct value with your reasoning.

## IMPORTANT

- Pay close attention to number formatting ({number_format}). Many errors come from misinterpreting decimal separators vs. thousands separators.
- Check for common OCR misreads: 0/O, 1/l/I, 5/S, 8/B, 6/G.
- Check for sign errors: is this a credit shown in parentheses or with "CR"?
- Check if the value includes or excludes VAT/tax.
- If the discrepancy is a math issue (quantity x rate != amount), check whether the utility applied rounding, minimum charges, or adjustment factors.

{domain_knowledge}

{few_shot_context}

## OUTPUT FORMAT

Respond as JSON:

```json
{
  "corrected_value": "...",
  "corrected_value_parsed": 0.0,
  "original_extraction_correct": false,
  "audit_correct": true,
  "is_utility_adjustment": false,
  "explanation": "The extraction misread the decimal separator. The value '1.234,56' in EU format is 1234.56, not 1.23456.",
  "confidence": 0.95,
  "source_location": "page 2, charges table, row 3, amount column"
}
```