"""Stage 1 (invoicing) — Bronze ingest for the SOAP/XML invoicing system.

Bronze must preserve raw fidelity regardless of format, so each SOAP envelope is
copied **verbatim** into ``data/bronze/invoices/``. A ``manifest.csv`` catalogues
every ingested file with the same ingestion metadata used by the CSV side, plus
a light read of the invoice id / SOAP message id to aid discovery.

No shredding happens here — that is silver's job.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

from common import (
    BRONZE_INVOICES_DIR,
    LANDING_INVOICES_DIR,
    ensure_dir,
    list_files,
    log,
    new_batch_id,
    now_iso,
    read_csv,
    read_text,
    write_csv,
    write_text,
)

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
INV_NS = "urn:demo:invoicing"
NS = {"soap": SOAP_NS, "inv": INV_NS}

MANIFEST_FIELDS = ["_source_file", "invoice_id", "message_id", "_ingested_at", "_batch_id"]
MANIFEST_PATH = os.path.join(BRONZE_INVOICES_DIR, "manifest.csv")


def _catalog_fields(xml_text: str) -> tuple[str, str]:
    """Light parse for the manifest: return (invoice_id, message_id)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return "", ""
    invoice = root.find(".//inv:Invoice", NS)
    message = root.find(".//inv:MessageId", NS)
    invoice_id = invoice.get("id", "") if invoice is not None else ""
    message_id = message.text.strip() if message is not None and message.text else ""
    return invoice_id, message_id


def ingest() -> int:
    """Copy invoice envelopes verbatim to bronze and append to the manifest."""
    landing_files = list_files(LANDING_INVOICES_DIR, ".xml")
    if not landing_files:
        log("bronze", "invoices: no landing files — run --stage generate first")
        return 0

    ensure_dir(BRONZE_INVOICES_DIR)
    batch_id = new_batch_id()
    ingested_at = now_iso()

    manifest = read_csv(MANIFEST_PATH)  # append-only across runs
    for path in landing_files:
        source = os.path.basename(path)
        xml_text = read_text(path)

        # Preserve the raw payload byte-for-byte.
        write_text(os.path.join(BRONZE_INVOICES_DIR, source), xml_text)

        invoice_id, message_id = _catalog_fields(xml_text)
        manifest.append({
            "_source_file": source,
            "invoice_id": invoice_id,
            "message_id": message_id,
            "_ingested_at": ingested_at,
            "_batch_id": batch_id,
        })

    write_csv(MANIFEST_PATH, manifest, MANIFEST_FIELDS)
    log("bronze", f"invoices: catalogued {len(landing_files)} file(s) ({batch_id})")
    return len(landing_files)


def read_manifest() -> list[dict]:
    """Return the invoice ingestion manifest rows."""
    return read_csv(MANIFEST_PATH)


def list_bronze_xml() -> list[str]:
    """Return absolute paths of raw XML envelopes stored in bronze."""
    return list_files(BRONZE_INVOICES_DIR, ".xml")


if __name__ == "__main__":
    ingest()
