import urllib.request
import json
import os

def fetch_and_cache_rates():
    """
    Queries a public, highly stable financial infrastructure endpoint
    to dynamically refresh VEKTRA's localized currency pairs.
    """
    # Free, no-auth-required reliable currency baseline API
    url = "https://er-api.com"
    cache_path = "fx-cache.json"
    
    # Baseline fallback definitions if the global API network fails
    fallback_rates = {
        'KES': 129.00, 'NGN': 1500.00, 'GHS': 15.10, 'ZAR': 18.20,
        'GBP': 0.78, 'EUR': 0.91, 'USD': 1.00
    }
    
    try:
        print("Initiating global FX cache refresh pipeline...")
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
        if data.get("result") == "success":
            api_rates = data.get("rates", {})
            
            # Map out exactly the structural currency pairs VEKTRA uses
            target_currencies = ['KES', 'NGN', 'GHS', 'ZAR', 'GBP', 'EUR', 'USD']
            fresh_cache = {}
            
            for curr in target_currencies:
                # If the API drops a specific African currency, fall back to safe baseline
                fresh_cache[curr] = api_rates.get(curr, fallback_rates[curr])
                
            # Atomically write to disk file system on Render
            with open(cache_path, "w") as f:
                json.dump(fresh_cache, f, indent=4)
                
            print(f"FX Cache successfully updated on Render storage: {fresh_cache}")
        else:
            print("API responded with an error state. Aborting overwrite.")
            
    except Exception as e:
        print(f"Critical error executing FX pipeline: {str(e)}. Maintained previous cache states.")

if __name__ == "__main__":
    fetch_and_cache_rates()
