from mcp.server.fastmcp import FastMCP
import mysql.connector
import os

mcp = FastMCP("database-query")

# Should load from env
DB_CONFIG = {
    'user': 'root',
    'password': 'your_password',
    'host': '127.0.0.1',
    'database': 'precious_insight'
}

@mcp.tool()
def query_database(query: str) -> str:
    """Execute a read-only SQL query"""
    if not query.lower().strip().startswith("select"):
        return "Error: Only SELECT queries are allowed"
    
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        cnx.close()
        return str(result)
    except Exception as e:
        return f"Database Error: {e}"

if __name__ == "__main__":
    mcp.run()
