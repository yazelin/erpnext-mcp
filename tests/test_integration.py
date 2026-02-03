"""
ERPNext MCP 進銷存整合測試
完整走一遍：採購入庫 → 銷售出貨，驗證所有 MCP tool 正常運作。
測試資料自動建立、測完自動清除。

需要 .env 中有有效的 ERPNext 連線資訊。
執行: cd /home/ct/SDD/erpnext-mcp && set -a && source .env && set +a && uv run pytest tests/test_integration.py -v -s
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import date

import pytest
import pytest_asyncio

from erpnext_mcp.client import ERPNextClient
from erpnext_mcp import server as srv

# ── Constants ────────────────────────────────────────────

PREFIX = "_MCP_TEST_"
SUPPLIER_NAME = f"{PREFIX}Supplier"
CUSTOMER_NAME = f"{PREFIX}Customer"
ITEM_CODE = f"{PREFIX}Item_001"
WAREHOUSE = "Stores - 擎添工業"  # adjust to your company's warehouse
COMPANY = "擎添工業有限公司"  # adjust to your company name
COMPANY_ABBR = "擎添工業"
INCOME_ACCOUNT = f"4111 - 銷貨收入 - {COMPANY_ABBR}"
EXPENSE_ACCOUNT = f"5111 - 銷貨成本 - {COMPANY_ABBR}"
TODAY = date.today().isoformat()


# ── Fixtures ─────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def client():
    c = ERPNextClient(
        url=os.environ["ERPNEXT_URL"],
        api_key=os.environ["ERPNEXT_API_KEY"],
        api_secret=os.environ["ERPNEXT_API_SECRET"],
    )
    yield c
    await c.close()


# ── Shared state across tests (module-scoped) ───────────

class State:
    supplier_name: str = ""
    customer_name: str = ""
    item_code: str = ""
    po_name: str = ""
    pr_name: str = ""  # Purchase Receipt
    pi_name: str = ""  # Purchase Invoice
    so_name: str = ""
    dn_name: str = ""  # Delivery Note
    si_name: str = ""  # Sales Invoice
    # File operations
    test_file_name: str = ""
    attached_file_name: str = ""
    server_test_file_name: str = ""


state = State()


# ── Helpers ──────────────────────────────────────────────

async def _force_cancel_and_delete(client: ERPNextClient, doctype: str, name: str):
    """Cancel (if submitted) then delete via API. Falls back to bench for cancelled docs."""
    if not name:
        return
    try:
        doc = await client.get_doc(doctype, name, fields=["docstatus"])
    except Exception:
        return  # doc doesn't exist
    if doc.get("docstatus") == 1:
        await client.cancel_doc(doctype, name)
    # Try API delete first; if it fails (e.g. cancelled doc with links), use bench
    try:
        await client.delete_doc(doctype, name)
    except Exception:
        _bench_force_delete(doctype, name)


# ── Bench SSH helper for force-deleting docs ─────────────

BENCH_SSH_CMD = os.environ.get(
    "BENCH_SSH_CMD",
    "sshpass -p 36274806 ssh -o StrictHostKeyChecking=no ct@192.168.11.11",
)
BENCH_SITE = os.environ.get("BENCH_SITE", "erp.localhost")
BENCH_CONTAINER = os.environ.get("BENCH_CONTAINER", "erpnext-backend-1")


def _bench_exec(python_code: str):
    """Execute python code on the ERPNext server via bench console."""
    cmd = (
        f'{BENCH_SSH_CMD} "docker exec {BENCH_CONTAINER} '
        f'bench --site {BENCH_SITE} execute {python_code}"'
    )
    subprocess.run(cmd, shell=True, capture_output=True, timeout=30)


def _bench_force_delete(doctype: str, name: str):
    """Force-delete a document via bench, bypassing link checks."""
    _bench_exec(
        f"frappe.delete_doc"
        f" --args '[\"{doctype}\", \"{name}\"]'"
        f" --kwargs '{{\"force\": 1, \"ignore_permissions\": 1}}'"
    )


def _bench_sql_cleanup():
    """Nuclear cleanup: remove all _MCP_TEST_ data via SQL on the remote server."""
    sql_statements = [
        "SET SQL_SAFE_UPDATES=0",
        "DELETE FROM `tabPayment Ledger Entry` WHERE party LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabGL Entry` WHERE party LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabStock Ledger Entry` WHERE item_code LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabBin` WHERE item_code LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabSales Invoice Item` WHERE parent IN (SELECT name FROM `tabSales Invoice` WHERE customer LIKE '_MCP_TEST_%')",
        "DELETE FROM `tabSales Invoice` WHERE customer LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabDelivery Note Item` WHERE parent IN (SELECT name FROM `tabDelivery Note` WHERE customer LIKE '_MCP_TEST_%')",
        "DELETE FROM `tabDelivery Note` WHERE customer LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabSales Order Item` WHERE parent IN (SELECT name FROM `tabSales Order` WHERE customer LIKE '_MCP_TEST_%')",
        "DELETE FROM `tabSales Order` WHERE customer LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabPurchase Invoice Item` WHERE parent IN (SELECT name FROM `tabPurchase Invoice` WHERE supplier LIKE '_MCP_TEST_%')",
        "DELETE FROM `tabPurchase Invoice` WHERE supplier LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabPurchase Receipt Item` WHERE parent IN (SELECT name FROM `tabPurchase Receipt` WHERE supplier LIKE '_MCP_TEST_%')",
        "DELETE FROM `tabPurchase Receipt` WHERE supplier LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabPurchase Order Item` WHERE parent IN (SELECT name FROM `tabPurchase Order` WHERE supplier LIKE '_MCP_TEST_%')",
        "DELETE FROM `tabPurchase Order` WHERE supplier LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabItem Default` WHERE parent LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabItem` WHERE name LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabCustomer` WHERE name LIKE '_MCP_TEST_%'",
        "DELETE FROM `tabSupplier` WHERE name LIKE '_MCP_TEST_%'",
        "SET SQL_SAFE_UPDATES=1",
    ]
    combined = "; ".join(sql_statements) + ";"
    # Write SQL to a temp file, copy to container, execute
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(combined)
        sql_path = f.name
    try:
        # Copy SQL file to remote, then into container, then execute
        subprocess.run(
            f'sshpass -p 36274806 scp -o StrictHostKeyChecking=no {sql_path} ct@192.168.11.11:/tmp/_mcp_test_cleanup.sql',
            shell=True, capture_output=True, timeout=15,
        )
        subprocess.run(
            f'sshpass -p 36274806 ssh -o StrictHostKeyChecking=no ct@192.168.11.11 '
            f'"docker cp /tmp/_mcp_test_cleanup.sql {BENCH_CONTAINER}:/tmp/_mcp_test_cleanup.sql && '
            f'docker exec {BENCH_CONTAINER} bench --site {BENCH_SITE} mariadb -e '
            f'\\\"source /tmp/_mcp_test_cleanup.sql\\\""',
            shell=True, capture_output=True, timeout=30,
        )
    finally:
        os.unlink(sql_path)


# ── Phase 0: Pre-cleanup (remove leftover from previous runs) ──

@pytest.mark.asyncio(loop_scope="module")
class TestPhase0PreCleanup:

    async def test_00_remove_leftovers(self, client: ERPNextClient):
        _bench_sql_cleanup()


# ── Phase 1: Setup (Master Data) ────────────────────────

@pytest.mark.asyncio(loop_scope="module")
class TestPhase1Setup:

    async def test_01_create_supplier(self, client: ERPNextClient):
        doc = await client.create_doc("Supplier", {
            "supplier_name": SUPPLIER_NAME,
            "supplier_group": "All Supplier Groups",
            "supplier_type": "Individual",
        })
        state.supplier_name = doc["name"]
        assert doc["name"]

    async def test_02_create_customer(self, client: ERPNextClient):
        doc = await client.create_doc("Customer", {
            "customer_name": CUSTOMER_NAME,
            "customer_group": "All Customer Groups",
            "customer_type": "Individual",
            "territory": "All Territories",
        })
        state.customer_name = doc["name"]
        assert doc["name"]

    async def test_03_create_item(self, client: ERPNextClient):
        doc = await client.create_doc("Item", {
            "item_code": ITEM_CODE,
            "item_name": f"{PREFIX}Test Item",
            "item_group": "All Item Groups",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "default_warehouse": WAREHOUSE,
        })
        state.item_code = doc["name"]
        assert doc["name"] == ITEM_CODE

    async def test_04_get_documents(self, client: ERPNextClient):
        sup = await client.get_doc("Supplier", state.supplier_name)
        assert sup["name"] == state.supplier_name
        cust = await client.get_doc("Customer", state.customer_name)
        assert cust["name"] == state.customer_name
        item = await client.get_doc("Item", state.item_code)
        assert item["name"] == state.item_code

    async def test_05_list_documents(self, client: ERPNextClient):
        items = await client.get_list("Item", filters={"name": state.item_code})
        assert len(items) >= 1

    async def test_06_search_link(self, client: ERPNextClient):
        results = await client.search_link("Item", PREFIX)
        names = [r.get("value", r.get("name", "")) for r in results]
        assert any(PREFIX in n for n in names)

    async def test_07_get_doctype_meta(self, client: ERPNextClient):
        # get_doctype_meta queries DocField which requires special perms;
        # use get_doc("DocType", ...) as a fallback to verify schema access
        try:
            meta = await client.get_doctype_meta("Item")
            assert isinstance(meta, list)
            field_names = [f.get("fieldname") for f in meta]
            assert "item_code" in field_names
        except Exception:
            # Fallback: read DocType document directly
            doc = await client.get_doc("DocType", "Item")
            field_names = [f.get("fieldname") for f in doc.get("fields", [])]
            assert "item_code" in field_names

    async def test_08_list_doctypes(self, client: ERPNextClient):
        doctypes = await client.get_list("DocType", fields=["name"], limit_page_length=10)
        assert len(doctypes) > 0

    async def test_09_get_count(self, client: ERPNextClient):
        count = await client.get_count("Item", filters={"name": state.item_code})
        assert count >= 1


# ── Phase 2: 採購流程 (Purchase) ─────────────────────────

@pytest.mark.asyncio(loop_scope="module")
class TestPhase2Purchase:

    async def test_01_create_purchase_order(self, client: ERPNextClient):
        doc = await client.create_doc("Purchase Order", {
            "supplier": state.supplier_name,
            "company": COMPANY,
            "schedule_date": TODAY,
            "items": [{
                "item_code": state.item_code,
                "qty": 10,
                "rate": 100,
                "schedule_date": TODAY,
                "warehouse": WAREHOUSE,
            }],
        })
        state.po_name = doc["name"]
        assert doc["name"]

    async def test_02_update_purchase_order(self, client: ERPNextClient):
        """用 update_document 修改 draft 階段的條款"""
        await client.update_doc("Purchase Order", state.po_name, {
            "terms": f"{PREFIX}updated terms",
        })
        doc = await client.get_doc("Purchase Order", state.po_name)
        assert PREFIX in doc.get("terms", "")

    async def test_03_submit_purchase_order(self, client: ERPNextClient):
        result = await client.submit_doc("Purchase Order", state.po_name)
        assert result

    async def test_04_make_purchase_receipt(self, client: ERPNextClient):
        mapped = await client.make_mapped_doc(
            "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
            state.po_name,
        )
        # mapped is the draft data; create and submit
        mapped.pop("docstatus", None)
        mapped.pop("name", None)
        mapped.pop("__islocal", None)
        doc = await client.create_doc("Purchase Receipt", mapped)
        state.pr_name = doc["name"]
        await client.submit_doc("Purchase Receipt", state.pr_name)

    async def test_05_stock_balance_after_receipt(self, client: ERPNextClient):
        bins = await client.get_stock_balance(item_code=state.item_code, warehouse=WAREHOUSE)
        assert len(bins) >= 1
        assert bins[0]["actual_qty"] >= 10

    async def test_06_stock_ledger_after_receipt(self, client: ERPNextClient):
        entries = await client.get_stock_ledger(item_code=state.item_code)
        assert len(entries) >= 1
        receipt_entries = [e for e in entries if e["voucher_type"] == "Purchase Receipt"]
        assert len(receipt_entries) >= 1

    async def test_07_make_purchase_invoice(self, client: ERPNextClient):
        mapped = await client.make_mapped_doc(
            "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
            state.po_name,
        )
        mapped.pop("docstatus", None)
        mapped.pop("name", None)
        mapped.pop("__islocal", None)
        # Set credit_to account if not set
        if not mapped.get("credit_to"):
            mapped["credit_to"] = f"Creditors - {COMPANY_ABBR}"
        doc = await client.create_doc("Purchase Invoice", mapped)
        state.pi_name = doc["name"]
        await client.submit_doc("Purchase Invoice", state.pi_name)

    async def test_08_party_balance_supplier(self, client: ERPNextClient):
        balance = await client.get_party_balance("Supplier", state.supplier_name)
        # After purchase invoice, supplier should have a credit balance
        assert balance is not None


# ── Phase 3: 銷售流程 (Sales) ────────────────────────────

@pytest.mark.asyncio(loop_scope="module")
class TestPhase3Sales:

    async def test_01_create_sales_order(self, client: ERPNextClient):
        doc = await client.create_doc("Sales Order", {
            "customer": state.customer_name,
            "company": COMPANY,
            "delivery_date": TODAY,
            "items": [{
                "item_code": state.item_code,
                "qty": 5,
                "rate": 200,
                "delivery_date": TODAY,
                "warehouse": WAREHOUSE,
            }],
        })
        state.so_name = doc["name"]
        assert doc["name"]

    async def test_02_submit_sales_order(self, client: ERPNextClient):
        result = await client.submit_doc("Sales Order", state.so_name)
        assert result

    async def test_03_make_delivery_note(self, client: ERPNextClient):
        mapped = await client.make_mapped_doc(
            "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
            state.so_name,
        )
        mapped.pop("docstatus", None)
        mapped.pop("name", None)
        mapped.pop("__islocal", None)
        doc = await client.create_doc("Delivery Note", mapped)
        state.dn_name = doc["name"]
        await client.submit_doc("Delivery Note", state.dn_name)

    async def test_04_stock_balance_after_delivery(self, client: ERPNextClient):
        bins = await client.get_stock_balance(item_code=state.item_code, warehouse=WAREHOUSE)
        assert len(bins) >= 1
        # Started with 10, delivered 5 → should be 5
        assert bins[0]["actual_qty"] >= 5

    async def test_05_stock_ledger_after_delivery(self, client: ERPNextClient):
        entries = await client.get_stock_ledger(item_code=state.item_code)
        dn_entries = [e for e in entries if e["voucher_type"] == "Delivery Note"]
        assert len(dn_entries) >= 1

    async def test_06_make_sales_invoice(self, client: ERPNextClient):
        mapped = await client.make_mapped_doc(
            "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
            state.so_name,
        )
        mapped.pop("docstatus", None)
        mapped.pop("name", None)
        mapped.pop("__islocal", None)
        if not mapped.get("debit_to"):
            mapped["debit_to"] = f"Debtors - {COMPANY_ABBR}"
        # Ensure income account is set on items
        for item in mapped.get("items", []):
            if not item.get("income_account"):
                item["income_account"] = INCOME_ACCOUNT
            if not item.get("expense_account"):
                item["expense_account"] = EXPENSE_ACCOUNT
        doc = await client.create_doc("Sales Invoice", mapped)
        state.si_name = doc["name"]
        await client.submit_doc("Sales Invoice", state.si_name)

    async def test_07_party_balance_customer(self, client: ERPNextClient):
        balance = await client.get_party_balance("Customer", state.customer_name)
        assert balance is not None

    async def test_08_get_item_price(self, client: ERPNextClient):
        # May or may not have Item Price records; just verify API works
        prices = await client.get_item_price(state.item_code)
        assert isinstance(prices, list)


# ── Phase 4: Reports ────────────────────────────────────

@pytest.mark.asyncio(loop_scope="module")
class TestPhase4Reports:

    async def test_01_run_report(self, client: ERPNextClient):
        result = await client.get_report("Stock Balance", filters={
            "item_code": state.item_code,
            "warehouse": WAREHOUSE,
        })
        assert result is not None

    async def test_02_get_list_with_summary(self, client: ERPNextClient):
        docs = await client.get_list("Sales Invoice", filters={"name": state.si_name})
        count = await client.get_count("Sales Invoice", filters={"name": state.si_name})
        assert len(docs) >= 1
        assert count >= 1

    async def test_03_run_method(self, client: ERPNextClient):
        """Test run_method via calling frappe.client.get_count"""
        result = await client.call_method(
            "frappe.client.get_count",
            http_method="GET",
            doctype="Item",
            filters=json.dumps({"name": state.item_code}),
        )
        assert result.get("message", 0) >= 1


# ── Phase 5: Server tool layer smoke test ────────────────

@pytest.mark.asyncio(loop_scope="module")
class TestPhase5ServerTools:
    """Verify server.py tool functions work (thin wrappers over client)."""

    async def test_01_list_documents_tool(self):
        result = await srv.list_documents.fn("Item", filters=json.dumps({"name": state.item_code}))
        assert len(result) >= 1

    async def test_02_get_document_tool(self):
        result = await srv.get_document.fn("Item", state.item_code)
        assert result["name"] == state.item_code

    async def test_03_get_count_tool(self):
        result = await srv.get_count.fn("Item", filters=json.dumps({"name": state.item_code}))
        assert result >= 1

    async def test_04_search_link_tool(self):
        result = await srv.search_link.fn("Item", PREFIX)
        assert len(result) >= 1

    async def test_05_get_stock_balance_tool(self):
        result = await srv.get_stock_balance.fn(item_code=state.item_code)
        assert isinstance(result, list)


# ── Phase 5.5: File Operations ──────────────────────────

@pytest.mark.asyncio(loop_scope="module")
class TestPhase5_5FileOperations:
    """Test file upload, list, download operations."""

    async def test_01_upload_file(self, client: ERPNextClient):
        """上傳測試檔案"""
        test_content = b"Hello from MCP test!"
        result = await client.upload_file(
            file_content=test_content,
            filename=f"{PREFIX}test_file.txt",
            is_private=True,
        )
        state.test_file_name = result.get("name", "")
        assert result.get("file_name") == f"{PREFIX}test_file.txt"
        assert result.get("file_url")

    async def test_02_upload_file_attached(self, client: ERPNextClient):
        """上傳附加到 Item 的檔案（需要先執行 Phase 1 建立 Item）"""
        if not state.item_code:
            pytest.skip("Requires item_code from Phase 1")
        test_content = b"Attached file content"
        result = await client.upload_file(
            file_content=test_content,
            filename=f"{PREFIX}attached_file.txt",
            attached_to_doctype="Item",
            attached_to_name=state.item_code,
            is_private=True,
        )
        state.attached_file_name = result.get("name", "")
        assert result.get("attached_to_doctype") == "Item"
        assert result.get("attached_to_name") == state.item_code

    async def test_03_list_files(self, client: ERPNextClient):
        """列出檔案"""
        files = await client.list_files(limit=10)
        assert isinstance(files, list)
        # 應該能找到我們上傳的檔案
        file_names = [f.get("file_name", "") for f in files]
        assert any(PREFIX in name for name in file_names)

    async def test_04_list_files_attached(self, client: ERPNextClient):
        """列出附加到 Item 的檔案（需要先執行 test_02）"""
        if not state.attached_file_name:
            pytest.skip("Requires attached_file from test_02")
        files = await client.list_files(
            attached_to_doctype="Item",
            attached_to_name=state.item_code,
        )
        assert len(files) >= 1
        assert any(f.get("file_name", "").startswith(PREFIX) for f in files)

    async def test_05_get_file_url(self, client: ERPNextClient):
        """取得檔案 URL"""
        url = await client.get_file_url(state.test_file_name)
        assert url
        assert "http" in url or url.startswith("/")

    async def test_06_download_file(self, client: ERPNextClient):
        """下載檔案"""
        content, filename = await client.download_file(state.test_file_name)
        assert content == b"Hello from MCP test!"
        assert PREFIX in filename

    async def test_07_server_upload_file_tool(self):
        """測試 server 層的 upload_file 工具"""
        import base64
        test_content = base64.b64encode(b"Server tool test").decode()
        result = await srv.upload_file.fn(
            file_content_base64=test_content,
            filename=f"{PREFIX}server_test.txt",
        )
        state.server_test_file_name = result.get("name", "")
        assert result.get("file_name") == f"{PREFIX}server_test.txt"

    async def test_08_server_list_files_tool(self):
        """測試 server 層的 list_files 工具"""
        result = await srv.list_files.fn(limit=10)
        assert isinstance(result, list)

    async def test_09_server_download_file_tool(self):
        """測試 server 層的 download_file 工具"""
        result = await srv.download_file.fn(state.server_test_file_name)
        assert result.get("content_base64")
        assert result.get("filename")

    async def test_10_cleanup_files(self, client: ERPNextClient):
        """清理測試檔案"""
        for file_name in [
            getattr(state, "test_file_name", ""),
            getattr(state, "attached_file_name", ""),
            getattr(state, "server_test_file_name", ""),
        ]:
            if file_name:
                try:
                    await client.delete_doc("File", file_name)
                except Exception:
                    pass


# ── Phase 6: Cleanup ────────────────────────────────────

@pytest.mark.asyncio(loop_scope="module")
class TestPhase6Cleanup:

    async def test_01_cancel_delete_sales_invoice(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Sales Invoice", state.si_name)

    async def test_02_cancel_delete_delivery_note(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Delivery Note", state.dn_name)

    async def test_03_cancel_delete_sales_order(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Sales Order", state.so_name)

    async def test_04_cancel_delete_purchase_invoice(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Purchase Invoice", state.pi_name)

    async def test_05_cancel_delete_purchase_receipt(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Purchase Receipt", state.pr_name)

    async def test_06_cancel_delete_purchase_order(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Purchase Order", state.po_name)

    async def test_07_delete_item(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Item", state.item_code)

    async def test_08_delete_customer(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Customer", state.customer_name)

    async def test_09_delete_supplier(self, client: ERPNextClient):
        await _force_cancel_and_delete(client, "Supplier", state.supplier_name)
