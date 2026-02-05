"""Azure Function: Blob trigger for invoice processing."""
import azure.functions as func
import logging
import json
import httpx

app = func.FunctionApp()

API_WEBHOOK_URL = "http://localhost:8000/webhook/blob-trigger"


@app.blob_trigger(arg_name="blob", path="imported/{name}", connection="AzureWebJobsStorage")
def process_invoice_blob(blob: func.InputStream):
    """Triggered when a new file is uploaded to the 'imported' container."""
    logging.info(f"Blob trigger fired: {blob.name}, size: {blob.length} bytes")

    try:
        # Notify the API webhook
        payload = {
            "blob_name": blob.name,
            "container": "imported",
            "content_length": blob.length,
        }

        response = httpx.post(API_WEBHOOK_URL, json=payload, timeout=30)
        response.raise_for_status()

        logging.info(f"Webhook notified successfully: {response.json()}")
    except Exception as e:
        logging.error(f"Failed to process blob {blob.name}: {e}")
        raise
