# MCP Tool API 參考

ERPNext MCP Server 提供 19 個工具，分為 CRUD、報表、工作流、輔助、庫存交易五大類。

---

## CRUD

### list_documents

列出指定 DocType 的文件清單。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱，如 `"Sales Order"` |
| fields | list[str] | N | 回傳欄位，預設 `["name"]` |
| filters | str | N | JSON 篩選條件，如 `'{"status": "Open"}'` 或 `'[["status","=","Open"]]'` |
| or_filters | str | N | JSON OR 篩選條件 |
| order_by | str | N | 排序，如 `"creation desc"` |
| limit_start | int | N | 分頁起始（預設 0） |
| limit_page_length | int | N | 回傳筆數（預設 20，最大 100） |

```json
// 範例
{"doctype": "Customer", "fields": ["name", "customer_name"], "filters": "{\"customer_type\": \"Individual\"}", "limit_page_length": 10}
```

---

### get_document

取得單一文件。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |
| name | str | Y | 文件名稱/ID |
| fields | list[str] | N | 指定回傳欄位 |

```json
{"doctype": "Sales Order", "name": "SO-00001", "fields": ["name", "status", "grand_total"]}
```

---

### create_document

建立新文件。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |
| data | str | Y | JSON 字串，欄位值 |

```json
{"doctype": "Customer", "data": "{\"customer_name\": \"Test Customer\", \"customer_type\": \"Individual\", \"customer_group\": \"All Customer Groups\", \"territory\": \"All Territories\"}"}
```

含子表（child table）範例：
```json
{"doctype": "Sales Order", "data": "{\"customer\": \"CUST-001\", \"company\": \"My Company\", \"delivery_date\": \"2025-12-31\", \"items\": [{\"item_code\": \"ITEM-001\", \"qty\": 10, \"rate\": 100}]}"}
```

---

### update_document

更新現有文件。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |
| name | str | Y | 文件名稱/ID |
| data | str | Y | JSON 字串，要更新的欄位 |

```json
{"doctype": "Sales Order", "name": "SO-00001", "data": "{\"delivery_date\": \"2025-12-31\"}"}
```

---

### delete_document

刪除文件。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |
| name | str | Y | 文件名稱/ID |

```json
{"doctype": "Customer", "name": "CUST-001"}
```

---

## 報表

### run_report

執行 ERPNext 報表。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| report_name | str | Y | 報表名稱，如 `"Stock Balance"` |
| filters | str | N | JSON 篩選條件 |

```json
{"report_name": "Stock Balance", "filters": "{\"company\": \"擎添工業有限公司\"}"}
```

---

### get_count

取得文件計數。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |
| filters | str | N | JSON 篩選條件 |

```json
{"doctype": "Sales Invoice", "filters": "{\"status\": \"Unpaid\"}"}
```

---

### get_list_with_summary

列出文件並附帶總筆數。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |
| fields | list[str] | N | 回傳欄位 |
| filters | str | N | JSON 篩選條件 |
| order_by | str | N | 排序 |
| limit_page_length | int | N | 回傳筆數（預設 20） |

回傳格式：`{"data": [...], "total_count": 123}`

---

## 工作流

### submit_document

提交可提交的文件（docstatus 0→1）。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |
| name | str | Y | 文件名稱/ID |

```json
{"doctype": "Sales Invoice", "name": "SINV-00001"}
```

---

### cancel_document

取消已提交的文件（docstatus 1→2）。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |
| name | str | Y | 文件名稱/ID |

---

### run_method

呼叫 ERPNext 白名單方法。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| method | str | Y | 方法路徑，如 `"frappe.client.get_count"` |
| http_method | str | N | `"GET"` 或 `"POST"`（預設 POST） |
| args | str | N | JSON 字串，關鍵字參數 |

```json
{"method": "frappe.client.get_count", "http_method": "GET", "args": "{\"doctype\": \"Customer\"}"}
```

---

## 輔助

### list_doctypes

列出可用的 DocType 名稱。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| module | str | N | 模組篩選，如 `"Selling"`, `"Stock"`, `"Accounts"` |
| is_submittable | bool | N | 只列出可提交的 DocType |
| limit | int | N | 最大筆數（預設 100） |

---

### search_link

連結欄位搜尋（自動完成）。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | 目標 DocType |
| txt | str | Y | 搜尋文字 |
| filters | str | N | JSON 篩選條件 |
| page_length | int | N | 最大筆數（預設 20） |

---

### get_doctype_meta

取得 DocType 的欄位定義。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| doctype | str | Y | DocType 名稱 |

回傳欄位：`fieldname`, `fieldtype`, `label`, `reqd`, `options`

---

## 庫存與交易

### get_stock_balance

從 Bin 表取得即時庫存餘額。**對 `item_code` 做精確比對**。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| item_code | str | N | 品項代碼（精確比對） |
| warehouse | str | N | 倉庫 |

回傳欄位：`item_code`, `warehouse`, `actual_qty`, `reserved_qty`, `ordered_qty`, `projected_qty`

> ⚠️ 回傳空陣列代表「找不到 Bin 紀錄」，可能是真的零庫存，也可能是 item_code 拼錯
> 或缺少公司前綴（例如系統實際是 `CTOS-KV-N40DT` 但只查了 `KV-N40DT`）。
> 此時請改用 [`find_items`](#find_items) 或 [`get_item_details`](#get_item_details) 模糊確認。

---

### get_item_price

查詢品項價格。**對 `item_code` 做精確比對**。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| item_code | str | Y | 品項代碼（精確比對） |
| price_list | str | N | 價格表名稱，如 `"Standard Selling"` |

回傳欄位：`item_code`, `price_list`, `price_list_rate`, `currency`, `uom`

---

### find_items

跨 `name` / `item_name` / `item_code` 做 `like %keyword%` 的 OR 模糊搜尋。
用來解決「使用者用原廠型號查詢，但系統 item_code 有公司前綴」的情境。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| keyword | str | Y | 搜尋關鍵字（部分代碼、原廠型號、品名片段皆可） |
| item_group | str | N | 限定 item_group |
| brand | str | N | 限定品牌 |
| include_disabled | bool | N | 是否包含已停用品項（預設 `False`） |
| limit | int | N | 最多回傳幾筆（預設 20） |

回傳欄位：`name`, `item_code`, `item_name`, `item_group`, `brand`, `stock_uom`, `disabled`, `has_variants`

範例：
```
find_items(keyword="KV-N40DT")
→ [{"name": "CTOS-KV-N40DT", "item_name": "KV-N40DT 基本模組", ...}, ...]
```

---

### get_item_details

一次取得品項主檔 + 庫存餘額 + 價格清單，避免為了查一個品項要連打 3~4 支工具。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| name | str | N* | 精確 Item name/item_code |
| keyword | str | N* | 模糊關鍵字（name 沒命中時用） |
| warehouse | str | N | 套用在 stock 的倉庫過濾 |
| price_list | str | N | 套用在 prices 的價單過濾 |

*`name` 與 `keyword` 至少擇一。解析順序：`name` 直接 get → `keyword` 試精確 name → fallback `find_items` 取第 1 筆。

回傳結構：
```
{
  "item": {"name", "item_code", "item_name", "item_group", "brand", "stock_uom", ...},
  "stock": [{"item_code", "warehouse", "actual_qty", "projected_qty", ...}, ...],
  "prices": [{"item_code", "price_list", "price_list_rate", "currency", "uom"}, ...],
  "other_candidates": [{"name", "item_name"}, ...]  // 其他 fuzzy 候選
}
```
找不到時回 `{"error": "...", "hint": "..."}`。

---

### make_mapped_doc

從現有文件轉換建立新文件（文件轉換）。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| method | str | Y | 轉換方法路徑 |
| source_name | str | Y | 來源文件名稱/ID |

常用轉換方法：

| 方法 | 轉換 |
|------|------|
| `erpnext.selling.doctype.quotation.quotation.make_sales_order` | 報價單 → 銷售單 |
| `erpnext.selling.doctype.sales_order.sales_order.make_delivery_note` | 銷售單 → 出貨單 |
| `erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice` | 銷售單 → 銷售發票 |
| `erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice` | 出貨單 → 銷售發票 |
| `erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt` | 採購單 → 入庫單 |
| `erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice` | 採購單 → 採購發票 |

回傳 draft 文件 JSON，可修改後用 `create_document` 建立再 `submit_document` 提交。

---

### get_party_balance

查詢客戶或供應商的未結餘額。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| party_type | str | Y | `"Customer"` 或 `"Supplier"` |
| party | str | Y | 對象名稱/ID |

---

### get_stock_ledger

查詢庫存異動記錄。**對 `item_code` 做精確比對**；查不到時改用 [`find_items`](#find_items)。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| item_code | str | N | 品項代碼（精確比對） |
| warehouse | str | N | 倉庫 |
| limit | int | N | 最大筆數（預設 50） |

回傳欄位：`item_code`, `warehouse`, `posting_date`, `qty_after_transaction`, `actual_qty`, `voucher_type`, `voucher_no`

結果按 `posting_date desc, posting_time desc` 排序。
