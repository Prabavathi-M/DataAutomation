# Snowflake MCP Server Guide

This guide explains how this project exposes a Snowflake query function through
the Model Context Protocol (MCP). It is written for developers who are new to
MCP, environment variables, Python packages, and Snowflake connections.

## 1. What We Built

The project has two Python modules:

```text
python_excersices/
    server.py          MCP server and tool registration
    snowflake_tool.py  Snowflake connection and query execution
    creds.env          Local credentials; never commit this file
```

The request flow is:

```text
MCP client
    sends SQL only
        |
        v
server.py
    registers run_snowflake_query
        |
        v
snowflake_tool.py
    loads local creds.env
    connects to Snowflake
    executes SQL
        |
        v
Snowflake rows returned to the MCP client
```

The MCP client does not need to receive the username, password, or other
connection settings. Those values stay on the machine running the MCP server.

## 2. Prerequisites

Use Python 3.10 or newer. Confirm the interpreter and pip that will be used:

```powershell
python --version
python -m pip --version
```

Always prefer `python -m pip` instead of a standalone `pip` command. This makes
sure that packages are installed into the same Python interpreter that runs the
server.

## 3. Install Dependencies

Install the MCP SDK, Snowflake connector, and dotenv loader:

```powershell
python -m pip install mcp snowflake-connector-python python-dotenv
```

To install all project dependencies:

```powershell
python -m pip install -r requirements.txt
```

The important pinned packages in this project are:

```text
mcp==2.2.0
python-dotenv==1.2.3
snowflake-connector-python==4.7.3
```

To install MCP and automatically add the installed version to
`requirements.txt`, use this PowerShell command:

```powershell
python -m pip install mcp
python -m pip freeze | Select-String "^mcp==" | ForEach-Object { $_.Line } | Add-Content .\requirements.txt
```

Check the installed MCP version:

```powershell
python -c "from importlib.metadata import version; print(version('mcp'))"
```

## 4. Store Credentials Locally

Create `python_excersices/creds.env` with your own values:

```env
SNOWFLAKE_USER=<snowflake_username>
SNOWFLAKE_PASSWORD=<snowflake_password>
SNOWFLAKE_ACCOUNT=<organization-account_identifier>
SNOWFLAKE_DATABASE=<database_name>
SNOWFLAKE_SCHEMA=<schema_name>
SNOWFLAKE_ROLE=<role_name>
SNOWFLAKE_WAREHOUSE=<warehouse_name>
```

Do not place real values in documentation, source code, screenshots, chat, or
MCP request JSON.

The account value must be the Snowflake account identifier from Snowsight. Do
not include the protocol or endpoint path:

```text
Correct:   organization-account_name
Incorrect: https://organization-account_name.snowflakecomputing.com
Incorrect: organization-account_name.snowflakecomputing.com/session/v1/login-request
```

The project `.gitignore` contains rules for the local files:

```gitignore
config.json
creds.env
```

The `creds.env` rule matches `python_excersices/creds.env` in this project.

## 5. Snowflake Connector Code

The file `python_excersices/snowflake_tool.py` loads the local environment file
and defines the reusable query function:

```python
import os
from pathlib import Path

from dotenv import load_dotenv
import snowflake.connector


load_dotenv(Path(__file__).with_name("creds.env"), override=True)


def run_snowflake_query(sql: str):
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    )
    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results
```

  ### Line-by-line explanation

  #### Import modules

  ```python
  import os
  ```

  `os` is part of Python's standard library. It gives the program access to
  operating-system features, including environment variables. We use
  `os.getenv()` later to read the Snowflake settings without writing the actual
  values into Python source code.

  ```python
  from pathlib import Path
  ```

  `Path` is a standard Python class for working with file paths. It is safer and
  more portable than manually joining strings with `\\` or `/`.

  ```python
  from dotenv import load_dotenv
  ```

  `load_dotenv` comes from the `python-dotenv` package. It reads `KEY=value`
  lines from a local dotenv file and places them into the current Python
  process's environment.

  ```python
  import snowflake.connector
  ```

  This imports the Snowflake Python connector. It provides the
  `snowflake.connector.connect()` function used to create a Snowflake session.

  #### Load the local credentials

  ```python
  load_dotenv(Path(__file__).with_name("creds.env"), override=True)
  ```

  This statement has four useful parts:

  1. `__file__` is the path of the current module,
     `snowflake_tool.py`.
  2. `Path(__file__)` turns that path into a `Path` object.
  3. `.with_name("creds.env")` changes only the filename, so Python looks for
     `creds.env` in the same directory as `snowflake_tool.py`.
  4. `load_dotenv(...)` reads the file and loads its values into the process.

  `override=True` means values from the local `creds.env` replace values with
  the same names that may already exist in the terminal environment. This is
  useful when a terminal has an old `SNOWFLAKE_ACCOUNT` value left over from a
  previous test.

  For example, this dotenv line:

  ```env
  SNOWFLAKE_DATABASE=MY_LEARNING
  ```

  becomes available to Python as an environment variable named
  `SNOWFLAKE_DATABASE`. The value is still local to the server process; it is
  not sent in the MCP request.

  #### Read individual environment variables

  ```python
  os.getenv("SNOWFLAKE_DATABASE")
  ```

  `os.getenv(name)` looks up the environment variable with that name and
  returns its value as a string. For example:

  ```python
  database = os.getenv("SNOWFLAKE_DATABASE")
  ```

  If the variable exists, `database` receives its value. If it does not exist,
  `os.getenv()` returns `None` by default. It does not read `creds.env` by
  itself; `load_dotenv()` must run first, or the variables must already be set
  by the operating system or MCP client configuration.

  You can provide a safe fallback for non-secret settings:

  ```python
  schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
  ```

  Do not provide a password fallback in source code. A missing password should
  be fixed in the environment instead of hard-coded.

  #### Create the Snowflake connection

  ```python
  conn = snowflake.connector.connect(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
  )
  ```

  `connect()` uses the locally loaded values to authenticate and create a
  Snowflake session. The variables mean:

  | Variable | Purpose |
  | --- | --- |
  | `SNOWFLAKE_USER` | Snowflake login username |
  | `SNOWFLAKE_PASSWORD` | Snowflake login password |
  | `SNOWFLAKE_ACCOUNT` | Snowflake organization/account identifier |
  | `SNOWFLAKE_DATABASE` | Database used by the session |
  | `SNOWFLAKE_SCHEMA` | Default schema used by the session |
  | `SNOWFLAKE_ROLE` | Role used for permissions |
  | `SNOWFLAKE_WAREHOUSE` | Virtual warehouse used to execute queries |

  The connection object is stored in `conn`. It represents the authenticated
  session, not the query result.

  #### Create a cursor and execute SQL

  ```python
  cur = conn.cursor()
  cur.execute(sql)
  ```

  `conn.cursor()` creates a cursor, which is the object used to send SQL and
  read results. The `sql` parameter is the string supplied by the MCP client,
  for example `select * from products;`.

  `execute(sql)` sends that SQL to Snowflake. Snowflake then parses, authorizes,
  and runs it. A connection error happens before this line can run; a SQL error
  such as an invalid column name happens at this line.

  #### Fetch and clean up

  ```python
  results = cur.fetchall()
  cur.close()
  conn.close()
  return results
  ```

  `fetchall()` retrieves all rows produced by the query as Python tuples. The
  rows are stored in `results` before the cursor and connection are closed.
  Closing both objects releases client and Snowflake resources. Finally,
  `return results` sends the rows back to the MCP wrapper in `server.py`.

  For production code, a `try/finally` block is stronger because it closes the
  cursor and connection even when SQL raises an exception. The simple version
  above is kept here to match the current learning implementation.

  ### `load_dotenv` versus `os.getenv`

  These functions have different jobs:

  ```text
  creds.env file
      |
      | load_dotenv(...)
      v
  process environment
      |
      | os.getenv("SNOWFLAKE_PASSWORD")
      v
  Python connection arguments
  ```

  Without `load_dotenv`, this code may return `None`:

  ```python
  password = os.getenv("SNOWFLAKE_PASSWORD")
  ```

  With `load_dotenv` executed first, it reads the local ignored file and the
  same `os.getenv` call can retrieve the value. Neither function sends the
  credential to the MCP client. They are local operations performed by the
  server process.

### Why `load_dotenv` is required

`os.getenv("SNOWFLAKE_USER")` reads an operating-system environment variable.
It does not automatically read a file named `creds.env`.

This line loads the file located beside the Python module:

```python
load_dotenv(Path(__file__).with_name("creds.env"), override=True)
```

Using `Path(__file__)` means the server can be started from another working
directory. `override=True` ensures a stale environment variable from an older
terminal session does not override the corrected local file.

## 6. MCP Server Code

The installed SDK is MCP 2.x. The current server implementation is:

```python
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
```

### Line-by-line explanation

#### Import the MCP server class

```python
from mcp.server.mcpserver import MCPServer
```

`MCPServer` is the server class provided by MCP 2.x. It manages the MCP
protocol, receives requests from an MCP client, advertises available tools, and
sends tool results back to the client.

The import path matters. Older examples may use `Server` or `Tool` from a
different MCP version. This project uses `mcp==2.2.0`, where `MCPServer` is the
supported high-level server class.

#### Import the Snowflake function

```python
from snowflake_tool import run_snowflake_query
```

This imports the function that does the real Snowflake work. The function lives
in a separate module so that database access and MCP protocol code have clear,
separate responsibilities:

```text
server.py          receives MCP requests and returns MCP results
snowflake_tool.py  loads credentials and executes Snowflake SQL
```

The import does not send credentials to the MCP client. It makes the local
Python function available to the server process.

#### Create the MCP server

```python
server = MCPServer(name="Snowflake MCP Server")
```

This creates one MCP server object and gives it a human-readable name. At this
point the object exists, but it has no custom tools registered yet.

#### Register a tool with the decorator

```python
@server.tool(
    name="run_snowflake_query",
    description="Execute SQL queries on Snowflake and return results",
    structured_output=True,
)
```

`@server.tool(...)` is a decorator. A decorator receives the function directly
below it and registers that function as an MCP tool.

The options describe the public MCP interface:

| Option | Meaning |
| --- | --- |
| `name` | Name the MCP client uses to call the tool |
| `description` | Human-readable explanation shown to the client |
| `structured_output=True` | The result follows a structured Python return type that MCP serializes |

The client calls the registered name `run_snowflake_query`; it does not need to
know the Python wrapper function's name.

#### Define the MCP wrapper function

```python
def run_snowflake_query_tool(sql: str) -> dict[str, list[list[object]]]:
```

This function is the MCP tool handler. It accepts one argument:

```python
sql: str
```

The type annotation says that `sql` should be a string containing SQL. The
return annotation documents the result shape: a dictionary containing a
`rows` key, whose value is a list of rows, where each row is a list of values.

The handler has a different Python name, `run_snowflake_query_tool`, because
`run_snowflake_query` is already the imported Snowflake function. The MCP name
is explicitly set in the decorator, so the client still calls
`run_snowflake_query`.

#### Call the Snowflake function

```python
rows = run_snowflake_query(sql)
```

The wrapper forwards the SQL to `snowflake_tool.py`. That function loads the
local credentials, opens a Snowflake connection, executes the SQL, fetches the
rows, closes the connection, and returns the rows to this wrapper.

Credentials are not parameters of the MCP tool. The only user-supplied tool
argument is `sql`.

#### Convert rows into structured output

```python
return {"rows": [list(row) for row in rows]}
```

Snowflake commonly returns each row as a Python tuple, for example:

```python
("Beverages", "Coca Cola")
```

The list comprehension converts every tuple into a list:

```python
[["Beverages", "Coca Cola"]]
```

The outer dictionary gives the response a named `rows` field. This makes the
result easier for an MCP client to inspect and serialize as JSON.

The complete request path is:

```text
MCP client sends {"sql": "select * from products;"}
  |
  v
run_snowflake_query_tool(sql)
  |
  v
run_snowflake_query(sql)
  |
  v
Snowflake returns tuple rows
  |
  v
MCP wrapper returns {"rows": [[...], [...]]}
```

#### Start only when the file is run directly

```python
if __name__ == "__main__":
    server.run()
```

Python sets `__name__` to `"__main__"` when you run:

```powershell
python server.py
```

Therefore, `server.run()` starts only in that case. When another script runs
`import server` for a test, the server object and tool registration are loaded,
but the process does not unexpectedly start waiting for MCP input.

#### Start the MCP event loop

```python
server.run()
```

With no transport argument, MCP uses its default stdio transport. The server
reads protocol messages from standard input and writes protocol responses to
standard output. It may appear to be idle in a terminal because it is waiting
for an MCP client; that is normal.

The decorator makes `run_snowflake_query` available to the MCP client. The
client sends an argument like this:

```json
{
  "sql": "select * from products;"
}
```

It does not send credentials. The handler returns rows in a JSON-friendly
format:

```json
{
  "rows": [
    ["Beverages", "Coca Cola"],
    [null, "Pepsi"]
  ]
}
```

## 7. Configure MCP in VS Code

This project includes the workspace configuration file:

```text
.vscode/mcp.json
```

Its contents are:

```json
{
  "servers": {
    "snowflake": {
      "type": "stdio",
      "command": "python",
      "args": [
        "${workspaceFolder}/python_excersices/server.py"
      ]
    }
  }
}
```

Each setting has a specific purpose:

| Setting | Meaning |
| --- | --- |
| `snowflake` | The name of this MCP server configuration |
| `type: stdio` | VS Code starts the server as a local process and communicates through standard input/output |
| `command: python` | Uses the Python interpreter available to VS Code |
| `args` | Passes the path of `server.py` to Python |
| `${workspaceFolder}` | Resolves to the opened DataAutomation folder |

The configuration deliberately does not contain a username, password, or
account value. When VS Code starts `server.py`, `snowflake_tool.py` loads the
ignored local `python_excersices/creds.env` file.

### Configure and test in VS Code

1. Open the `DataAutomation` folder as the VS Code workspace.
2. Confirm that `python_excersices/creds.env` exists locally.
3. Confirm that the selected Python interpreter has the project dependencies.
4. Open the MCP tools view in VS Code and start or enable the `snowflake` server.
    In VS Code: 
        Press Ctrl+Shift+P.     
        Search for MCP: List Servers.       
        Select the snowflake server.       
        Choose Start Server.       
        Open Chat with Ctrl+Alt+I.     
        Select Agent mode.     
        Click the Tools button near the chat input.  
        Confirm run_snowflake_query is listed and enabled.
5. Confirm that `run_snowflake_query` appears as an available tool.
6. Call it with only the SQL argument:

```json
{
  "sql": "select * from products;"
}
```

The MCP request does not include credentials. The local server reads them and
returns the query rows.

### Test the server process outside VS Code

From the workspace root, first check the code and registration:

```powershell
python -m py_compile .\python_excersices\snowflake_tool.py .\python_excersices\server.py
python -c "import sys; sys.path.insert(0, '.\\python_excersices'); import server; print([tool.name for tool in server.server._tool_manager.list_tools()])"
```

Expected output includes:

```text
['run_snowflake_query']
```

Do not use a normal terminal to type SQL after running `python server.py`.
That process is waiting for MCP protocol messages, not plain SQL text. Use the
VS Code MCP client to invoke the tool.

## 8. Start the MCP Server

Run these commands from the directory containing the server modules:

```powershell
Set-Location .\python_excersices
python server.py
```

The server uses the MCP stdio transport. It may appear to wait without printing
anything; that is normal because it is waiting for an MCP client to send a
request. Do not type SQL directly into the server terminal. Send SQL through an
MCP client.

## 9. Safe Validation Commands

### Compile the modules

This checks Python syntax without making a Snowflake connection:

```powershell
Set-Location .\python_excersices
python -m py_compile snowflake_tool.py server.py
```

### Check package availability without printing secrets

```powershell
python -c "import importlib.util; print('mcp:', bool(importlib.util.find_spec('mcp'))); print('dotenv:', bool(importlib.util.find_spec('dotenv'))); print('snowflake:', bool(importlib.util.find_spec('snowflake')))"
```

### Check MCP registration

```powershell
Set-Location .\python_excersices
python -c "import server; print('MCP server import: ok'); print('registered tools:', [tool.name for tool in server.server._tool_manager.list_tools()])"
```

Expected output includes:

```text
MCP server import: ok
registered tools: ['run_snowflake_query']
```

### Test Snowflake authentication safely

This query verifies the session without printing identity values:

```powershell
Set-Location .\python_excersices
python -c "from snowflake_tool import run_snowflake_query; rows=run_snowflake_query('select current_account(), current_user(), current_database(), current_schema()'); print('Snowflake connection: ok'); print('metadata rows:', len(rows))"
```

Do not print `os.environ`, the contents of `creds.env`, or the password in a
diagnostic command.

### Run a data query directly for troubleshooting

```powershell
Set-Location .\python_excersices
python -c "from snowflake_tool import run_snowflake_query; rows=run_snowflake_query('select * from products;'); print('rows:', len(rows)); [print(row) for row in rows]"
```

## 10. Example Query and Result

For the sample `products` table, this request:

```sql
SELECT * FROM products;
```

returned:

```text
('Beverages', 'Coca Cola')
(None, 'Pepsi')
(None, 'Sprite')
(None, 'Fanta')
('Snacks', 'Lays')
(None, 'Doritos')
(None, 'Kurkure')
```

The `NULL` category values indicate that the table stores the category only on
the first row of each group.

To carry the last non-null category forward, use a real ordering column. Do not
write `ORDER BY nulls`; Snowflake interprets `nulls` as a column name and raises
`invalid identifier 'NULLS'`.

Example:

```sql
SELECT
    LAST_VALUE(category) IGNORE NULLS OVER (
        ORDER BY product_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS category,
    brand_name
FROM products;
```

Replace `product_id` with the actual column that defines row order. If the table
has no ordering column, the database cannot reliably determine which category
comes before another row.

## 11. Troubleshooting Guide

### `ModuleNotFoundError: No module named 'mcp'`

Install into the same interpreter used to run the server:

```powershell
python -m pip install mcp
python -c "import mcp; print('mcp installed')"
```

If the package is installed but Python cannot import it, compare the commands:

```powershell
python --version
python -m pip --version
python -c "import sys; print(sys.executable)"
```

The paths should point to the same Python installation.

### `ImportError: cannot import name 'Tool' from 'mcp.server'`

This means the code targets an older MCP API. MCP 2.x uses `MCPServer`:

```python
from mcp.server.mcpserver import MCPServer
```

Register tools with `@server.tool(...)` instead of importing `Tool` from
`mcp.server`.

The dependency version and implementation must agree:

```text
mcp==2.2.0
```

### Snowflake `404 Not Found` during login

Example symptom:

```text
404 Not Found: post <account>.snowflakecomputing.com/session/v1/login-request
```

This occurs before SQL compilation. Check the account identifier, not the SQL.
Use the organization/account identifier from Snowsight and do not include
`https://` or the Snowflake endpoint path.

Also check for stale variables in the current terminal. The project uses
`override=True` so the local `creds.env` value wins when the module loads.

### Snowflake `invalid identifier 'NULLS'`

This comes from a query such as:

```sql
ORDER BY nulls
```

Replace `nulls` with a real ordering column. `NULLS FIRST` and `NULLS LAST` are
ordering options, not a standalone column named `nulls`.

### The server appears to do nothing

That is expected for stdio transport. The server is waiting for MCP messages.
First validate imports and registration in a separate command, then launch it
from the MCP client configuration.

## 12. Secret-Safety Checklist

Before committing changes, run:

```powershell
git check-ignore -v config.json python_excersices/creds.env
git ls-files --error-unmatch config.json python_excersices/creds.env
```

The second command should report that the paths are not tracked. Check for
credential patterns in tracked files without printing ignored files:

```powershell
git grep -n -I -E "SNOWFLAKE_PASSWORD|SNOWFLAKE_USER|SNOWFLAKE_ACCOUNT|github_pat_|password[[:space:]]*[:=]|api[_-]?key[[:space:]]*[:=]"
```

Important rules:

1. Never commit `creds.env` or files containing passwords and tokens.
2. Never paste credentials into an MCP request.
3. Never print all environment variables for debugging.
4. Use placeholders in documentation and examples.
5. If a real credential is accidentally displayed or committed, revoke or
   rotate it and create a replacement.

## 13. Useful Git Commands

Review local changes:

```powershell
git status --short
git diff -- .gitignore requirements.txt python_excersices/server.py python_excersices/snowflake_tool.py
```

Check ignored files:

```powershell
git status --short --ignored -- config.json python_excersices/creds.env
git check-ignore -v config.json python_excersices/creds.env
```

Check whether a path exists anywhere in reachable Git history without printing
file contents:

```powershell
git rev-list --objects --all | Select-String "config\.json|creds\.env"
```

## 14. Key Lessons

- MCP transports requests and results; it does not manage your Snowflake
  password automatically.
- `os.getenv()` reads process environment variables, while `load_dotenv()`
  loads values from a local file into that environment.
- `.gitignore` prevents untracked files from being added, but it does not erase
  a secret that was already committed.
- Package APIs change. Pin the version and use the API belonging to that version.
- Test in layers: Python syntax, package imports, MCP registration, Snowflake
  connection, and finally SQL correctness.