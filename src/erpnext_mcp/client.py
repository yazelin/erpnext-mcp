from __future__ import annotations
import json
from typing import Any

import httpx


class ERPNextClient:
    def __init__(self, url: str, api_key: str, api_secret: str):
        self.base_url = url.rstrip("/")
        self.headers = {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        client = await self._get_client()
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    # --- CRUD ---

    async def get_list(
        self,
        doctype: str,
        fields: list[str] | None = None,
        filters: Any = None,
        or_filters: Any = None,
        order_by: str | None = None,
        limit_start: int = 0,
        limit_page_length: int = 20,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "limit_start": limit_start,
            "limit_page_length": limit_page_length,
        }
        if fields:
            params["fields"] = json.dumps(fields)
        if filters:
            params["filters"] = json.dumps(filters)
        if or_filters:
            params["or_filters"] = json.dumps(or_filters)
        if order_by:
            params["order_by"] = order_by

        result = await self._request("GET", f"/api/resource/{doctype}", params=params)
        return result.get("data", [])

    async def get_doc(self, doctype: str, name: str, fields: list[str] | None = None) -> dict:
        params = {}
        if fields:
            params["fields"] = json.dumps(fields)
        result = await self._request("GET", f"/api/resource/{doctype}/{name}", params=params)
        return result.get("data", {})

    async def create_doc(self, doctype: str, data: dict) -> dict:
        result = await self._request("POST", f"/api/resource/{doctype}", json={"data": json.dumps(data)})
        return result.get("data", {})

    async def update_doc(self, doctype: str, name: str, data: dict) -> dict:
        result = await self._request("PUT", f"/api/resource/{doctype}/{name}", json={"data": json.dumps(data)})
        return result.get("data", {})

    async def delete_doc(self, doctype: str, name: str) -> dict:
        result = await self._request("DELETE", f"/api/resource/{doctype}/{name}")
        return result

    # --- Methods ---

    async def call_method(self, method: str, http_method: str = "GET", **kwargs) -> Any:
        if http_method.upper() == "POST":
            result = await self._request("POST", f"/api/method/{method}", json=kwargs)
        else:
            result = await self._request("GET", f"/api/method/{method}", params=kwargs)
        return result

    # --- Document workflow ---

    async def submit_doc(self, doctype: str, name: str) -> dict:
        doc = await self.get_doc(doctype, name)
        doc["docstatus"] = 1
        return await self.call_method(
            "frappe.client.submit",
            http_method="POST",
            doc=json.dumps(doc),
        )

    async def cancel_doc(self, doctype: str, name: str) -> dict:
        return await self.call_method(
            "frappe.client.cancel",
            http_method="POST",
            doctype=doctype,
            name=name,
        )

    async def get_count(self, doctype: str, filters: Any = None) -> int:
        params: dict[str, Any] = {"doctype": doctype}
        if filters:
            params["filters"] = json.dumps(filters)
        result = await self.call_method("frappe.client.get_count", **params)
        return result.get("message", 0)

    async def get_report(self, report_name: str, filters: Any = None) -> Any:
        params: dict[str, Any] = {"report_name": report_name}
        if filters:
            params["filters"] = json.dumps(filters)
        return await self.call_method("frappe.desk.query_report.run", **params)

    async def search_link(self, doctype: str, txt: str, filters: Any = None, page_length: int = 20) -> list:
        params: dict[str, Any] = {
            "doctype": doctype,
            "txt": txt,
            "page_length": page_length,
        }
        if filters:
            params["filters"] = json.dumps(filters)
        result = await self.call_method("frappe.desk.search.search_link", **params)
        return result.get("message", result.get("results", []))

    async def get_doctype_meta(self, doctype: str) -> dict:
        result = await self.call_method("frappe.client.get_list", doctype="DocField", filters=json.dumps({"parent": doctype}), fields=json.dumps(["fieldname", "fieldtype", "label", "reqd", "options"]), limit_page_length="0")
        return result.get("message", [])

    # --- Inventory & Trading helpers ---

    async def get_stock_balance(
        self, item_code: str | None = None, warehouse: str | None = None,
    ) -> list[dict]:
        filters: dict[str, Any] = {}
        if item_code:
            filters["item_code"] = item_code
        if warehouse:
            filters["warehouse"] = warehouse
        result = await self._request(
            "GET", "/api/resource/Bin",
            params={
                "fields": json.dumps(["item_code", "warehouse", "actual_qty", "reserved_qty", "ordered_qty", "projected_qty"]),
                "filters": json.dumps(filters),
                "limit_page_length": 0,
            },
        )
        return result.get("data", [])

    async def get_item_price(
        self, item_code: str, price_list: str | None = None,
    ) -> list[dict]:
        filters: dict[str, Any] = {"item_code": item_code}
        if price_list:
            filters["price_list"] = price_list
        result = await self._request(
            "GET", "/api/resource/Item Price",
            params={
                "fields": json.dumps(["item_code", "price_list", "price_list_rate", "currency", "uom"]),
                "filters": json.dumps(filters),
                "limit_page_length": 0,
            },
        )
        return result.get("data", [])

    async def make_mapped_doc(self, method: str, source_name: str) -> dict:
        result = await self.call_method(
            method, http_method="POST", source_name=source_name,
        )
        return result.get("message", result)

    async def get_party_balance(self, party_type: str, party: str) -> Any:
        result = await self.call_method(
            "erpnext.accounts.utils.get_balance_on",
            http_method="GET",
            party_type=party_type,
            party=party,
        )
        return result.get("message", 0)

    async def get_stock_ledger(
        self, item_code: str | None = None, warehouse: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        filters: dict[str, Any] = {}
        if item_code:
            filters["item_code"] = item_code
        if warehouse:
            filters["warehouse"] = warehouse
        result = await self._request(
            "GET", "/api/resource/Stock Ledger Entry",
            params={
                "fields": json.dumps(["item_code", "warehouse", "posting_date", "qty_after_transaction", "actual_qty", "voucher_type", "voucher_no"]),
                "filters": json.dumps(filters),
                "order_by": "posting_date desc, posting_time desc",
                "limit_page_length": limit,
            },
        )
        return result.get("data", [])
