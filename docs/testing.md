# 整合測試說明

## 概述

`tests/test_integration.py` 是一個端對端整合測試，完整走過採購入庫 → 銷售出貨的進銷存流程，驗證所有 19 個 MCP tool 正常運作。測試資料自動建立、測完自動清除。

## 環境需求

- Python >= 3.11
- ERPNext 實例（可連線）
- `.env` 檔案包含：
  ```
  ERPNEXT_URL=http://ct.erp
  ERPNEXT_API_KEY=<your_api_key>
  ERPNEXT_API_SECRET=<your_api_secret>
  ```
- API 使用者需有以下角色：System Manager, Item Manager, Purchase Master Manager, Sales Master Manager, Delivery Manager, Delivery User, Maintenance User
- SSH 可連線至 ERPNext 主機（Phase 0 清除用）

## 執行方式

```bash
cd /home/ct/SDD/erpnext-mcp
set -a && source .env && set +a
uv run pytest tests/test_integration.py -v
```

## 測試結構（43 項測試）

### Phase 0: 預清除 (1 test)
透過 SSH → Docker → MariaDB 強制清除所有 `_MCP_TEST_` 前綴的殘留資料，確保測試冪等性。清除範圍包含：
- Payment Ledger Entry, GL Entry, Stock Ledger Entry, Bin
- Sales Invoice, Delivery Note, Sales Order
- Purchase Invoice, Purchase Receipt, Purchase Order
- Item, Customer, Supplier

### Phase 1: 主資料建立 (9 tests)
| 測試 | 驗證 Tool |
|------|-----------|
| test_01 建立供應商 | `create_document` |
| test_02 建立客戶 | `create_document` |
| test_03 建立品項 | `create_document` |
| test_04 取得文件 | `get_document` |
| test_05 列表查詢 | `list_documents` |
| test_06 連結搜尋 | `search_link` |
| test_07 欄位定義 | `get_doctype_meta` |
| test_08 列出 DocType | `list_doctypes` |
| test_09 計數查詢 | `get_count` |

### Phase 2: 採購流程 (8 tests)
| 測試 | 驗證 Tool |
|------|-----------|
| test_01 建立採購單 | `create_document` |
| test_02 修改採購單 | `update_document` |
| test_03 提交採購單 | `submit_document` |
| test_04 PO→PR→提交 | `make_mapped_doc`, `create_document`, `submit_document` |
| test_05 庫存餘額 | `get_stock_balance` |
| test_06 庫存異動 | `get_stock_ledger` |
| test_07 PO→PI→提交 | `make_mapped_doc`, `create_document`, `submit_document` |
| test_08 供應商餘額 | `get_party_balance` |

### Phase 3: 銷售流程 (8 tests)
| 測試 | 驗證 Tool |
|------|-----------|
| test_01 建立銷售單 | `create_document` |
| test_02 提交銷售單 | `submit_document` |
| test_03 SO→DN→提交 | `make_mapped_doc`, `create_document`, `submit_document` |
| test_04 庫存餘額 | `get_stock_balance` |
| test_05 庫存異動 | `get_stock_ledger` |
| test_06 SO→SI→提交 | `make_mapped_doc`, `create_document`, `submit_document` |
| test_07 客戶餘額 | `get_party_balance` |
| test_08 品項價格 | `get_item_price` |

### Phase 4: 報表 (3 tests)
| 測試 | 驗證 Tool |
|------|-----------|
| test_01 執行報表 | `run_report` |
| test_02 帶計數查詢 | `get_list_with_summary` |
| test_03 呼叫方法 | `run_method` |

### Phase 5: Server Tool 層 (5 tests)
透過 `server.py` 的 `@mcp.tool()` 函式（使用 `.fn` 屬性）驗證 MCP tool 層正常運作：
- `list_documents`, `get_document`, `get_count`, `search_link`, `get_stock_balance`

### Phase 6: 清除 (9 tests)
按相依性反序取消並刪除所有測試資料：
1. Sales Invoice → Delivery Note → Sales Order
2. Purchase Invoice → Purchase Receipt → Purchase Order
3. Item → Customer → Supplier

每步使用 `cancel_document` → `delete_document`。若 API 刪除失敗（如已取消文件有 Payment Ledger Entry 連結），自動透過 SSH bench 強制刪除。

## 測試常數

```python
PREFIX = "_MCP_TEST_"
COMPANY = "擎添工業有限公司"
COMPANY_ABBR = "擎添工業"
WAREHOUSE = "Stores - 擎添工業"
INCOME_ACCOUNT = "4111 - 銷貨收入 - 擎添工業"
EXPENSE_ACCOUNT = "5111 - 銷貨成本 - 擎添工業"
```

## 冪等性

測試可在任意時間重複執行。Phase 0 的 SQL 清除確保即使上次測試中斷或清除失敗，下次執行仍能正常通過。
