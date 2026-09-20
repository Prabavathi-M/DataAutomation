from mcp.server.mcpserver import MCPServer
from snowflake_tool import run_snowflake_query

server = MCPServer(name="Snowflake MCP Server")


@server.tool(
    name="run_snowflake_query",
    description="Execute SQL queries on Snowflake and return results",
    structured_output=True,
)
def run_snowflake_query_tool(sql: str) -> dict[str, list[list[object]]]:
    rows = run_snowflake_query(sql)
    return {"rows": [list(row) for row in rows]}

if __name__ == "__main__":
    server.run()
