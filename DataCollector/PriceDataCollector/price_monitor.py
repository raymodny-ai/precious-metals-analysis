import time
import os
import mysql.connector
from datetime import datetime
from metals_api_client import MetalsAPIClient

# Database config - should be in config file or env
DB_CONFIG = {
    'user': 'root',
    'password': 'your_password', # Placeholder
    'host': '127.0.0.1',
    'database': 'precious_insight'
}

def save_prices(data):
    if not data or not data.get('success'):
        print(f"Invalid data received: {data}")
        return

    rates = data.get('rates', {})
    # Timestamp from API or current time
    timestamp = datetime.fromtimestamp(data.get('timestamp', time.time()))
    
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        
        add_price = ("INSERT INTO metal_prices "
                     "(metal_type, price_usd, timestamp, source) "
                     "VALUES (%s, %s, %s, %s)")
        
        # Map symbols to metal types
        symbol_map = {
            'XAU': 'gold',
            'XAG': 'silver',
            'XPT': 'platinum',
            'XPD': 'palladium'
        }

        for symbol, rate in rates.items():
            if symbol in symbol_map:
                # If base is USD, rate is how much Metal you get for 1 USD.
                # Price in USD = 1 / rate
                price = 1 / rate if rate else 0
                
                data_price = (symbol_map[symbol], price, timestamp, 'Metals-API')
                cursor.execute(add_price, data_price)
        
        cnx.commit()
        cursor.close()
        cnx.close()
        print(f"Prices saved at {timestamp}")
        
    except mysql.connector.Error as err:
        print(f"Database error: {err}")

def monitor(interval=60):
    client = MetalsAPIClient()
    print("Starting price monitor...")
    while True:
        data = client.get_latest_rates()
        save_prices(data)
        time.sleep(interval)

if __name__ == "__main__":
    monitor()
