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

從 Bin 表取得即時庫存餘額。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| item_code | str | N | 品項代碼 |
| warehouse | str | N | 倉庫 |

回傳欄位：`item_code`, `warehouse`, `actual_qty`, `reserved_qty`, `ordered_qty`, `projected_qty`

---

### get_item_price

查詢品項價格。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| item_code | str | Y | 品項代碼 |
| price_list | str | N | 價格表名稱，如 `"Standard Selling"` |

回傳欄位：`item_code`, `price_list`, `price_list_rate`, `currency`, `uom`

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

查詢庫存異動記錄。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| item_code | str | N | 品項代碼 |
| warehouse | str | N | 倉庫 |
| limit | int | N | 最大筆數（預設 50） |

回傳欄位：`item_code`, `warehouse`, `posting_date`, `qty_after_transaction`, `actual_qty`, `voucher_type`, `voucher_no`

結果按 `posting_date desc, posting_time desc` 排序。
