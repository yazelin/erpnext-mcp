from __future__ import annotations
import json
import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP

from .client import ERPNextClient

load_dotenv()

mcp = FastMCP(
    "ERPNext",
    instructions="MCP Server for ERPNext REST API - CRUD, reports, workflow operations",
)

_client: ERPNextClient | None = None


def get_client() -> ERPNextClient:
    global _client
    if _client is None:
        url = os.environ.get("ERPNEXT_URL", "http://ct.erp")
        api_key = os.environ["ERPNEXT_API_KEY"]
        api_secret = os.environ["ERPNEXT_API_SECRET"]
        _client = ERPNextClient(url, api_key, api_secret)
    return _client


# ── CRUD ──────────────────────────────────────────────


@mcp.tool()
async def list_documents(
    doctype: str,
    fields: list[str] | None = None,
    filters: str | None = None,
    or_filters: str | None = None,
    order_by: str | None = None,
    limit_start: int = 0,
    limit_page_length: int = 20,
) -> list[dict]:
    """List documents of a given DocType with optional filtering, sorting and pagination.

    Args:
        doctype: ERPNext DocType name (e.g. "Sales Order", "Customer")
        fields: List of field names to return. Defaults to ["name"].
        filters: JSON string of filters, e.g. '{"status": "Open"}' or '[["status","=","Open"]]'
        or_filters: JSON string of OR filters
        order_by: Sort expression, e.g. "creation desc"
        limit_start: Pagination offset
        limit_page_length: Number of records to return (max 100)
    """
    f = json.loads(filters) if filters else None
    of = json.loads(or_filters) if or_filters else None
    return await get_client().get_list(
        doctype, fields=fields, filters=f, or_filters=of,
        order_by=order_by, limit_start=limit_start, limit_page_length=limit_page_length,
    )


@mcp.tool()
async def get_document(doctype: str, name: str, fields: list[str] | None = None) -> dict:
    """Get a single document by DocType and name.

    Args:
        doctype: ERPNext DocType name
        name: Document name/ID
        fields: Optional list of fields to return
    """
    return await get_client().get_doc(doctype, name, fields=fields)


@mcp.tool()
async def create_document(doctype: str, data: str) -> dict:
    """Create a new document.

    Args:
        doctype: ERPNext DocType name
        data: JSON string of field values, e.g. '{"customer_name": "Test", "customer_type": "Individual"}'
    """
    return await get_client().create_doc(doctype, json.loads(data))


@mcp.tool()
async def update_document(doctype: str, name: str, data: str) -> dict:
    """Update an existing document.

    Args:
        doctype: ERPNext DocType name
        name: Document name/ID
        data: JSON string of fields to update
    """
    return await get_client().update_doc(doctype, name, json.loads(data))


@mcp.tool()
async def delete_document(doctype: str, name: str) -> dict:
    """Delete a document.

    Args:
        doctype: ERPNext DocType name
        name: Document name/ID
    """
    return await get_client().delete_doc(doctype, name)


# ── Reports ───────────────────────────────────────────


@mcp.tool()
async def run_report(report_name: str, filters: str | None = None) -> Any:
    """Execute an ERPNext report.

    Args:
        report_name: Name of the report
        filters: Optional JSON string of report filters
    """
    f = json.loads(filters) if filters else None
    return await get_client().get_report(report_name, filters=f)


@mcp.tool()
async def get_count(doctype: str, filters: str | None = None) -> int:
    """Get document count for a DocType with optional filters.

    Args:
        doctype: ERPNext DocType name
        filters: Optional JSON string of filters
    """
    f = json.loads(filters) if filters else None
    return await get_client().get_count(doctype, filters=f)


@mcp.tool()
async def get_list_with_summary(
    doctype: str,
    fields: list[str] | None = None,
    filters: str | None = None,
    order_by: str | None = None,
    limit_page_length: int = 20,
) -> dict:
    """Get a list of documents along with total count.

    Args:
        doctype: ERPNext DocType name
        fields: Fields to return
        filters: Optional JSON string of filters
        order_by: Sort expression
        limit_page_length: Number of records
    """
    f = json.loads(filters) if filters else None
    client = get_client()
    docs = await client.get_list(doctype, fields=fields, filters=f, order_by=order_by, limit_page_length=limit_page_length)
    count = await client.get_count(doctype, filters=f)
    return {"data": docs, "total_count": count}


# ── Workflow ──────────────────────────────────────────


@mcp.tool()
async def submit_document(doctype: str, name: str) -> dict:
    """Submit a submittable document (e.g. Sales Invoice).

    Args:
        doctype: ERPNext DocType name
        name: Document name/ID
    """
    return await get_client().submit_doc(doctype, name)


@mcp.tool()
async def cancel_document(doctype: str, name: str) -> dict:
    """Cancel a submitted document.

    Args:
        doctype: ERPNext DocType name
        name: Document name/ID
    """
    return await get_client().cancel_doc(doctype, name)


@mcp.tool()
async def run_method(method: str, http_method: str = "POST", args: str | None = None) -> Any:
    """Call a server-side method (whitelisted API).

    Args:
        method: Dotted method path, e.g. "frappe.client.get_list" or "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note"
        http_method: GET or POST (default POST)
        args: Optional JSON string of keyword arguments
    """
    kwargs = json.loads(args) if args else {}
    return await get_client().call_method(method, http_method=http_method, **kwargs)


# ── Helpers ───────────────────────────────────────────


@mcp.tool()
async def list_doctypes(module: str | None = None, is_submittable: bool | None = None, limit: int = 100) -> list[str]:
    """List all available DocType names.

    Args:
        module: Optional module filter (e.g. "Selling", "Stock", "Accounts")
        is_submittable: Optional filter for submittable doctypes only
        limit: Max results (default 100)
    """
    filters: dict[str, Any] = {}
    if module:
        filters["module"] = module
    if is_submittable is not None:
        filters["is_submittable"] = int(is_submittable)
    docs = await get_client().get_list(
        "DocType", fields=["name"], filters=filters or None,
        order_by="name asc", limit_page_length=limit,
    )
    return [d["name"] for d in docs]


@mcp.tool()
async def search_link(doctype: str, txt: str, filters: str | None = None, page_length: int = 20) -> list:
    """Search for link field values (autocomplete).

    Args:
        doctype: DocType to search in
        txt: Search text
        filters: Optional JSON string of filters
        page_length: Max results
    """
    f = json.loads(filters) if filters else None
    return await get_client().search_link(doctype, txt, filters=f, page_length=page_length)


@mcp.tool()
async def get_doctype_meta(doctype: str) -> list:
    """Get field definitions for a DocType.

    Args:
        doctype: ERPNext DocType name
    """
    return await get_client().get_doctype_meta(doctype)


# ── Inventory & Trading ──────────────────────────────


@mcp.tool()
async def get_stock_balance(item_code: str | None = None, warehouse: str | None = None) -> list[dict]:
    """Get real-time stock balance from Bin.

    Args:
        item_code: Optional item code to filter
        warehouse: Optional warehouse to filter
    """
    return await get_client().get_stock_balance(item_code=item_code, warehouse=warehouse)


@mcp.tool()
async def get_item_price(item_code: str, price_list: str | None = None) -> list[dict]:
    """Get item prices from Item Price records.

    Args:
        item_code: Item code to look up
        price_list: Optional price list name to filter (e.g. "Standard Selling")
    """
    return await get_client().get_item_price(item_code, price_list=price_list)


@mcp.tool()
async def make_mapped_doc(method: str, source_name: str) -> dict:
    """Create a new document mapped from an existing one (document conversion).

    Common methods:
    - erpnext.selling.doctype.quotation.quotation.make_sales_order (Quotation → Sales Order)
    - erpnext.selling.doctype.sales_order.sales_order.make_delivery_note (Sales Order → Delivery Note)
    - erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice (Sales Order → Sales Invoice)
    - erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice (Delivery Note → Sales Invoice)
    - erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt (PO → Purchase Receipt)
    - erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice (PO → Purchase Invoice)

    Args:
        method: Dotted path of the mapping method
        source_name: Name/ID of the source document
    """
    return await get_client().make_mapped_doc(method, source_name)


@mcp.tool()
async def get_party_balance(party_type: str, party: str) -> Any:
    """Get outstanding balance for a Customer or Supplier.

    Args:
        party_type: "Customer" or "Supplier"
        party: Party name/ID
    """
    return await get_client().get_party_balance(party_type, party)


@mcp.tool()
async def get_stock_ledger(item_code: str | None = None, warehouse: str | None = None, limit: int = 50) -> list[dict]:
    """Get stock ledger entries (inventory transaction history).

    Args:
        item_code: Optional item code filter
        warehouse: Optional warehouse filter
        limit: Max records to return (default 50)
    """
    return await get_client().get_stock_ledger(item_code=item_code, warehouse=warehouse, limit=limit)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
