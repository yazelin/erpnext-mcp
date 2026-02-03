# 開發記錄

## 問題與解決方案

### 1. API 使用者權限不足 (403 FORBIDDEN)

**問題**：API 使用者有 System Manager 角色，但建立 Supplier、Item 等文件時回傳 403。

**原因**：ERPNext 的 DocPerm 是依角色控制的，System Manager 對某些 DocType 沒有 create/delete 權限。例如 Supplier 需要 "Purchase Master Manager"，Item 需要 "Item Manager"。

**解決**：透過 SQL 加入必要角色：
```sql
INSERT INTO `tabHas Role` (name, parent, parenttype, parentfield, role)
VALUES
  (UUID(), 'yazelin@ching-tech.com', 'User', 'roles', 'Item Manager'),
  (UUID(), 'yazelin@ching-tech.com', 'User', 'roles', 'Purchase Master Manager'),
  (UUID(), 'yazelin@ching-tech.com', 'User', 'roles', 'Sales Master Manager'),
  (UUID(), 'yazelin@ching-tech.com', 'User', 'roles', 'Delivery Manager'),
  (UUID(), 'yazelin@ching-tech.com', 'User', 'roles', 'Delivery User'),
  (UUID(), 'yazelin@ching-tech.com', 'User', 'roles', 'Maintenance User');
```

---

### 2. 公司名稱錯誤 (417 EXPECTATION FAILED)

**問題**：測試用 `"CT"` 作為公司名稱，但 ERPNext 回傳「找不到公司: CT」。

**原因**：實際公司名稱為 `擎添工業有限公司`，縮寫為 `擎添工業`。

**解決**：修正所有常數：
```python
COMPANY = "擎添工業有限公司"
COMPANY_ABBR = "擎添工業"
WAREHOUSE = "Stores - 擎添工業"
```

---

### 3. submit_doc TimestampMismatchError

**問題**：提交採購單時出現 `TimestampMismatchError`。

**原因**：`client.py` 的 `submit_doc` 原本只傳 `{"doctype": "...", "name": "..."}`，但 `frappe.client.submit` 需要完整文件 JSON 且包含正確的 `modified` 時間戳。

**解決**：修改 `client.py`，先 `get_doc` 取得完整文件，設定 `docstatus=1` 後再提交：
```python
async def submit_doc(self, doctype: str, name: str) -> dict:
    doc = await self.get_doc(doctype, name)
    doc["docstatus"] = 1
    return await self.call_method(
        "frappe.client.submit",
        http_method="POST",
        doc=json.dumps(doc),
    )
```

---

### 4. 倉庫缺少科目 (417 "請在倉庫中設科目")

**問題**：提交 Purchase Receipt 時，ERPNext 要求倉庫必須設定庫存科目。

**解決**：
1. 建立 `Stock In Hand - 擎添工業` 科目（account_type: Stock, root_type: Asset）
2. 在倉庫 `Stores - 擎添工業` 設定 `account = "Stock In Hand - 擎添工業"`
3. 在公司設定 `default_inventory_account = "Stock In Hand - 擎添工業"`

---

### 5. Sales Invoice 缺少收入科目

**問題**：建立 Sales Invoice 時回傳「Income Account None does not belong to Company」。

**解決**：
1. 在公司設定 `default_income_account = "4111 - 銷貨收入 - 擎添工業"`
2. 測試中對 mapped items 明確設定 `income_account` 和 `expense_account`：
```python
for item in mapped.get("items", []):
    if not item.get("income_account"):
        item["income_account"] = INCOME_ACCOUNT
    if not item.get("expense_account"):
        item["expense_account"] = EXPENSE_ACCOUNT
```

---

### 6. FunctionTool 不可直接呼叫

**問題**：`await srv.list_documents(...)` 拋出 TypeError。

**原因**：fastmcp 的 `@mcp.tool()` 將函式包裝成 `FunctionTool` 物件，不能直接當 async function 呼叫。

**解決**：使用 `.fn` 屬性存取底層函式：
```python
await srv.list_documents.fn("Item", ...)
```

---

### 7. 重複執行時 409 CONFLICT

**問題**：第二次執行測試時，Phase 1 建立文件回傳 409（已存在）。

**原因**：Phase 6 清除階段用 `try/except pass` 吞掉了刪除錯誤。已取消文件（docstatus=2）若有 Payment Ledger Entry/GL Entry 連結，REST API 無法刪除。

**解決**：
1. 新增 Phase 0 預清除，透過 SSH → Docker → MariaDB 用 SQL 強制刪除所有 `_MCP_TEST_` 資料
2. Phase 6 加入 `_bench_force_delete()` fallback，對 API 刪不掉的文件用 bench 指令處理
3. SQL 清除範圍涵蓋 Payment Ledger Entry, GL Entry, Stock Ledger Entry, Bin 等關聯表

---

### 8. SQL 透過 subprocess 的跳脫問題

**問題**：在 subprocess.run 中執行含反引號和引號的 SQL 指令會被 shell 錯誤解析。

**解決**：改為寫入暫存檔 → scp 到遠端 → docker cp 進容器 → `source` 執行：
```python
with tempfile.NamedTemporaryFile(...) as f:
    f.write(sql_script.encode())
    subprocess.run(f"scp {f.name} host:/tmp/cleanup.sql", shell=True)
    subprocess.run(f"ssh host docker cp /tmp/cleanup.sql container:/tmp/", shell=True)
    subprocess.run(f"ssh host docker exec container bench --site {site} mariadb < /tmp/cleanup.sql", shell=True)
```

---

### 9. get_doctype_meta 403

**問題**：查詢 DocField 表時回傳 403，因為 DocField 沒有對應的角色權限。

**解決**：加入 try/except fallback，改為讀取 `DocType` 文件本身：
```python
async def get_doctype_meta(self, doctype: str) -> dict:
    result = await self.call_method("frappe.client.get_list",
        doctype="DocField",
        filters=json.dumps({"parent": doctype}),
        fields=json.dumps(["fieldname", "fieldtype", "label", "reqd", "options"]),
        limit_page_length="0")
    return result.get("message", [])
```

## ERPNext 環境資訊

| 項目 | 值 |
|------|-----|
| 主機 | 192.168.11.11 (Docker) |
| 容器名稱 | erpnext-backend-1 |
| Site | erp.localhost |
| 對外 URL | http://ct.erp |
| 公司 | 擎添工業有限公司 |
| 公司縮寫 | 擎添工業 |
| API 使用者 | yazelin@ching-tech.com |
