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

    # --- File operations ---

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        attached_to_doctype: str | None = None,
        attached_to_name: str | None = None,
        is_private: bool = True,
    ) -> dict:
        """上傳檔案到 ERPNext。

        Args:
            file_content: 檔案內容（bytes）
            filename: 檔案名稱
            attached_to_doctype: 附加到的 DocType（如 "Project"）
            attached_to_name: 附加到的文件名稱（如 "PROJ-0001"）
            is_private: 是否為私有檔案（預設 True）

        Returns:
            File 文件資料，包含 file_url 等
        """
        # 使用獨立的 httpx client 避免 header 衝突
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            # 準備 multipart form data
            files = {
                "file": (filename, file_content),
            }
            data: dict[str, str] = {
                "is_private": "1" if is_private else "0",
            }
            if attached_to_doctype:
                data["doctype"] = attached_to_doctype
            if attached_to_name:
                data["docname"] = attached_to_name

            resp = await client.post(
                "/api/method/upload_file",
                files=files,
                data=data,
                headers={
                    "Authorization": self.headers["Authorization"],
                    "Expect": "",  # 禁用 100-continue，避免 417 錯誤
                },
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("message", result)

    async def upload_file_from_url(
        self,
        file_url: str,
        filename: str | None = None,
        attached_to_doctype: str | None = None,
        attached_to_name: str | None = None,
        is_private: bool = True,
    ) -> dict:
        """從 URL 上傳檔案到 ERPNext。

        Args:
            file_url: 檔案來源 URL
            filename: 檔案名稱（可選，會從 URL 推斷）
            attached_to_doctype: 附加到的 DocType
            attached_to_name: 附加到的文件名稱
            is_private: 是否為私有檔案

        Returns:
            File 文件資料
        """
        # 使用獨立的 httpx client
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            data: dict[str, str] = {
                "file_url": file_url,
                "is_private": "1" if is_private else "0",
            }
            if filename:
                data["filename"] = filename
            if attached_to_doctype:
                data["doctype"] = attached_to_doctype
            if attached_to_name:
                data["docname"] = attached_to_name

            resp = await client.post(
                "/api/method/upload_file",
                data=data,
                headers={"Authorization": self.headers["Authorization"]},
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("message", result)

    async def list_files(
        self,
        attached_to_doctype: str | None = None,
        attached_to_name: str | None = None,
        is_private: bool | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """列出檔案。

        Args:
            attached_to_doctype: 過濾附加到的 DocType
            attached_to_name: 過濾附加到的文件名稱
            is_private: 過濾私有/公開檔案
            limit: 返回數量上限

        Returns:
            File 文件列表
        """
        filters: dict[str, Any] = {}
        if attached_to_doctype:
            filters["attached_to_doctype"] = attached_to_doctype
        if attached_to_name:
            filters["attached_to_name"] = attached_to_name
        if is_private is not None:
            filters["is_private"] = 1 if is_private else 0

        result = await self._request(
            "GET", "/api/resource/File",
            params={
                "fields": json.dumps([
                    "name", "file_name", "file_url", "file_size",
                    "attached_to_doctype", "attached_to_name",
                    "is_private", "creation", "modified",
                ]),
                "filters": json.dumps(filters) if filters else None,
                "order_by": "creation desc",
                "limit_page_length": limit,
            },
        )
        return result.get("data", [])

    async def get_file_url(self, file_name: str) -> str:
        """取得檔案的完整下載 URL。

        Args:
            file_name: File 文件的 name（如 "abc123.pdf"）

        Returns:
            完整的檔案 URL
        """
        doc = await self.get_doc("File", file_name)
        file_url = doc.get("file_url", "")
        if file_url and not file_url.startswith("http"):
            return f"{self.base_url}{file_url}"
        return file_url

    async def download_file(self, file_name: str) -> tuple[bytes, str]:
        """下載檔案內容。

        Args:
            file_name: File 文件的 name

        Returns:
            (檔案內容 bytes, 檔案名稱)
        """
        doc = await self.get_doc("File", file_name)
        file_url = doc.get("file_url", "")
        original_filename = doc.get("file_name", file_name)

        if not file_url:
            raise ValueError(f"File {file_name} has no file_url")

        client = await self._get_client()
        # 下載時不需要 Content-Type: application/json
        resp = await client.get(file_url)
        resp.raise_for_status()
        return resp.content, original_filename
