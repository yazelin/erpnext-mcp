# ERPNext MCP Server

MCP (Model Context Protocol) server for ERPNext REST API, built with [FastMCP](https://github.com/jlowin/fastmcp) and Python.

## Features

- **CRUD** — List, get, create, update, delete documents
- **Workflow** — Submit and cancel submittable documents
- **Reports** — Run ERPNext query reports
- **Schema** — Inspect DocType field definitions, list all DocTypes
- **Inventory** — Stock balance, stock ledger, item prices
- **Trading** — Document conversion (e.g. Quotation → Sales Order), party balance
- **Helpers** — Link search (autocomplete), document count, generic method calls

## Requirements

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- ERPNext instance with API key/secret

## Setup

```bash
# Clone the repo
git clone <repo-url> && cd erpnext-mcp

# Create .env file
cat > .env << 'EOF'
ERPNEXT_URL=https://your-erpnext-instance.com
ERPNEXT_API_KEY=your_api_key
ERPNEXT_API_SECRET=your_api_secret
EOF

# Install dependencies
uv sync
```

## Run

```bash
set -a && source .env && set +a && uv run erpnext-mcp
```

## Available Tools

| Tool | Description |
|---|---|
| `list_documents` | List documents with filters, sorting, pagination |
| `get_document` | Get a single document by name |
| `create_document` | Create a new document |
| `update_document` | Update an existing document |
| `delete_document` | Delete a document |
| `submit_document` | Submit a submittable document |
| `cancel_document` | Cancel a submitted document |
| `run_report` | Execute an ERPNext report |
| `get_count` | Get document count with optional filters |
| `get_list_with_summary` | List documents with total count |
| `run_method` | Call any whitelisted server-side method |
| `search_link` | Link field autocomplete search |
| `list_doctypes` | List all available DocType names |
| `get_doctype_meta` | Get field definitions for a DocType |
| `get_stock_balance` | Real-time stock balance from Bin |
| `get_stock_ledger` | Stock ledger entries (inventory history) |
| `get_item_price` | Item prices from price lists |
| `make_mapped_doc` | Document conversion (e.g. SO → DN) |
| `get_party_balance` | Outstanding balance for Customer/Supplier |

## MCP Client Configuration

Add to your MCP client config (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "erpnext": {
      "command": "uv",
      "args": ["--directory", "/path/to/erpnext-mcp", "run", "erpnext-mcp"],
      "env": {
        "ERPNEXT_URL": "https://your-erpnext-instance.com",
        "ERPNEXT_API_KEY": "your_api_key",
        "ERPNEXT_API_SECRET": "your_api_secret"
      }
    }
  }
}
```

## Project Structure

```
src/erpnext_mcp/
├── server.py   # MCP tool definitions (FastMCP)
├── client.py   # ERPNext REST API client (httpx async)
└── types.py    # Pydantic models
```

## License

MIT
