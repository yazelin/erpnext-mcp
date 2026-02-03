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


# ── File Operations ─────────────────────────────────


@mcp.tool()
async def upload_file(
    file_content_base64: str,
    filename: str,
    attached_to_doctype: str | None = None,
    attached_to_name: str | None = None,
    is_private: bool = True,
) -> dict:
    """Upload a file to ERPNext.

    Args:
        file_content_base64: File content encoded as base64 string
        filename: Name for the uploaded file (e.g. "report.pdf")
        attached_to_doctype: Optional DocType to attach file to (e.g. "Project", "Item")
        attached_to_name: Optional document name to attach file to (e.g. "PROJ-0001")
        is_private: Whether file should be private (default True)

    Returns:
        File document with file_url and other metadata
    """
    import base64
    file_content = base64.b64decode(file_content_base64)
    return await get_client().upload_file(
        file_content=file_content,
        filename=filename,
        attached_to_doctype=attached_to_doctype,
        attached_to_name=attached_to_name,
        is_private=is_private,
    )


@mcp.tool()
async def upload_file_from_url(
    file_url: str,
    filename: str | None = None,
    attached_to_doctype: str | None = None,
    attached_to_name: str | None = None,
    is_private: bool = True,
) -> dict:
    """Upload a file to ERPNext from a URL.

    Args:
        file_url: Source URL to fetch the file from
        filename: Optional name for the file (will be inferred from URL if not provided)
        attached_to_doctype: Optional DocType to attach file to
        attached_to_name: Optional document name to attach file to
        is_private: Whether file should be private (default True)

    Returns:
        File document with file_url and other metadata
    """
    return await get_client().upload_file_from_url(
        file_url=file_url,
        filename=filename,
        attached_to_doctype=attached_to_doctype,
        attached_to_name=attached_to_name,
        is_private=is_private,
    )


@mcp.tool()
async def list_files(
    attached_to_doctype: str | None = None,
    attached_to_name: str | None = None,
    is_private: bool | None = None,
    limit: int = 20,
) -> list[dict]:
    """List files in ERPNext, optionally filtered by attachment.

    Args:
        attached_to_doctype: Filter by DocType (e.g. "Project", "Item")
        attached_to_name: Filter by document name (e.g. "PROJ-0001")
        is_private: Filter by privacy (True=private, False=public, None=all)
        limit: Max number of files to return (default 20)

    Returns:
        List of File documents with name, file_name, file_url, file_size, etc.
    """
    return await get_client().list_files(
        attached_to_doctype=attached_to_doctype,
        attached_to_name=attached_to_name,
        is_private=is_private,
        limit=limit,
    )


@mcp.tool()
async def get_file_url(file_name: str) -> str:
    """Get the full download URL for a file.

    Args:
        file_name: The File document name (e.g. "abc123.pdf" or the hash-based name)

    Returns:
        Full URL to download the file
    """
    return await get_client().get_file_url(file_name)


@mcp.tool()
async def download_file(file_name: str) -> dict:
    """Download a file's content from ERPNext.

    Args:
        file_name: The File document name

    Returns:
        Dict with 'content_base64' (file content as base64) and 'filename' (original filename)
    """
    import base64
    content, filename = await get_client().download_file(file_name)
    return {
        "content_base64": base64.b64encode(content).decode("utf-8"),
        "filename": filename,
    }


# ── Supplier/Customer Details ──────────────────────────


@mcp.tool()
async def get_supplier_details(name: str | None = None, keyword: str | None = None) -> dict:
    """Get complete supplier details including address, phone, and contacts.

    Args:
        name: Exact supplier name (e.g. "SF0009-2 - 永心企業社")
        keyword: Search keyword to find supplier (e.g. "永心")

    Returns:
        Dict with supplier info, address (phone/fax), and contacts (our purchaser + their contacts)
    """
    client = get_client()

    # Find supplier
    if name:
        supplier = await client.get_doc("Supplier", name)
    elif keyword:
        suppliers = await client.get_list(
            "Supplier",
            fields=["name", "supplier_name", "supplier_group", "country"],
            filters={"name": ["like", f"%{keyword}%"]},
            limit_page_length=1,
        )
        if not suppliers:
            return {"error": f"找不到關鍵字「{keyword}」的供應商"}
        supplier = await client.get_doc("Supplier", suppliers[0]["name"])
    else:
        return {"error": "請提供 name 或 keyword"}

    supplier_name = supplier.get("name")

    # Get address (phone/fax)
    # Address title format: "代碼 地址", e.g. "SF0009-2 地址"
    code = supplier_name.split(" - ")[0] if " - " in supplier_name else supplier_name
    addresses = await client.get_list(
        "Address",
        fields=["address_title", "address_line1", "city", "pincode", "phone", "fax"],
        filters={"address_title": ["like", f"%{code}%"]},
        limit_page_length=5,
    )

    # Get contacts via Dynamic Link
    contacts = await client.get_list(
        "Contact",
        fields=["name", "first_name", "designation", "phone", "mobile_no", "email_id"],
        filters=[["Dynamic Link", "link_name", "=", supplier_name]],
        limit_page_length=50,
    )

    # Categorize contacts
    # 有 designation 的是我們的人（採購人員/業務人員），沒有的是對方的聯絡人
    our_contacts = []
    their_contacts = []
    for c in contacts:
        contact_info = {
            "name": c.get("first_name") or c.get("name"),
            "designation": c.get("designation") or "",
            "phone": c.get("phone") or c.get("mobile_no") or "",
            "email": c.get("email_id") or "",
        }
        if c.get("designation"):
            our_contacts.append(contact_info)
        else:
            their_contacts.append(contact_info)

    return {
        "supplier": {
            "name": supplier_name,
            "group": supplier.get("supplier_group"),
            "country": supplier.get("country"),
            "currency": supplier.get("default_currency"),
        },
        "address": addresses[0] if addresses else None,
        "our_contacts": our_contacts,
        "their_contacts": their_contacts,
    }


@mcp.tool()
async def get_customer_details(name: str | None = None, keyword: str | None = None) -> dict:
    """Get complete customer details including address, phone, and contacts.

    Args:
        name: Exact customer name (e.g. "CM0001 - 正達工程股份有限公司")
        keyword: Search keyword to find customer (e.g. "正達")

    Returns:
        Dict with customer info, address (phone/fax), and contacts (our sales + their contacts)
    """
    client = get_client()

    # Find customer
    if name:
        customer = await client.get_doc("Customer", name)
    elif keyword:
        customers = await client.get_list(
            "Customer",
            fields=["name", "customer_name", "customer_group", "territory"],
            filters={"name": ["like", f"%{keyword}%"]},
            limit_page_length=1,
        )
        if not customers:
            return {"error": f"找不到關鍵字「{keyword}」的客戶"}
        customer = await client.get_doc("Customer", customers[0]["name"])
    else:
        return {"error": "請提供 name 或 keyword"}

    customer_name = customer.get("name")

    # Get address (phone/fax)
    code = customer_name.split(" - ")[0] if " - " in customer_name else customer_name
    addresses = await client.get_list(
        "Address",
        fields=["address_title", "address_line1", "city", "pincode", "phone", "fax"],
        filters={"address_title": ["like", f"%{code}%"]},
        limit_page_length=5,
    )

    # Get contacts via Dynamic Link
    contacts = await client.get_list(
        "Contact",
        fields=["name", "first_name", "designation", "phone", "mobile_no", "email_id"],
        filters=[["Dynamic Link", "link_name", "=", customer_name]],
        limit_page_length=50,
    )

    # Categorize contacts
    # 有 designation 的是我們的人（採購人員/業務人員），沒有的是對方的聯絡人
    our_contacts = []
    their_contacts = []
    for c in contacts:
        contact_info = {
            "name": c.get("first_name") or c.get("name"),
            "designation": c.get("designation") or "",
            "phone": c.get("phone") or c.get("mobile_no") or "",
            "email": c.get("email_id") or "",
        }
        if c.get("designation"):
            our_contacts.append(contact_info)
        else:
            their_contacts.append(contact_info)

    return {
        "customer": {
            "name": customer_name,
            "group": customer.get("customer_group"),
            "territory": customer.get("territory"),
            "currency": customer.get("default_currency"),
        },
        "address": addresses[0] if addresses else None,
        "our_contacts": our_contacts,
        "their_contacts": their_contacts,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
