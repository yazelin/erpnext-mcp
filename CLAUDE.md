# ERPNext MCP Server

## Run
```bash
cd /home/ct/SDD/erpnext-mcp
set -a && source .env && set +a && uv run erpnext-mcp
```

## Structure
- `src/erpnext_mcp/server.py` - MCP tool definitions (fastmcp)
- `src/erpnext_mcp/client.py` - ERPNext REST API client (httpx async)
- `src/erpnext_mcp/types.py` - Pydantic models

## Auth
Uses `Authorization: token {api_key}:{api_secret}` header. Set `ERPNEXT_API_KEY` and `ERPNEXT_API_SECRET` in `.env`.

## Docs
- `docs/api-reference.md` - 19 個 MCP tool 的參數、型別與範例
- `docs/testing.md` - 整合測試說明（43 項測試、執行方式、Phase 結構）
- `docs/development-notes.md` - 開發記錄（問題與解決方案、環境資訊）

## Adding Tools
Add `@mcp.tool()` decorated async functions in `server.py`. Use `get_client()` for API calls. Filter/data params accept JSON strings to stay MCP-compatible.
