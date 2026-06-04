from mcp.server.fastmcp import FastMCP
import requests
import os

mcp = FastMCP("precious-metals-price")

@mcp.tool()
def get_current_gold_price() -> str:
    """Get current gold price in USD/oz"""
    api_key = os.getenv('METALS_API_KEY')
    if not api_key:
        return "Error: METALS_API_KEY not set"
    
    url = "https://metals-api.com/api/latest"
    params = {'access_key': api_key, 'base': 'USD', 'symbols': 'XAU'}
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get('success'):
            rate = data['rates']['XAU']
            # If base is USD, rate is XAU per USD. Price = 1/Rate
            price = 1 / rate if rate else 0
            return f"Current Gold Price: ${price:.2f}/oz"
        return f"Error fetching price: {data}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run()
