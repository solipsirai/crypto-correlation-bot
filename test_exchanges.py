import ccxt

exchanges_to_test = ['kucoin', 'gateio', 'kraken', 'okx']

for ex_id in exchanges_to_test:
    print(f"Testing {ex_id}...")
    ex_class = getattr(ccxt, ex_id)
    exchange = ex_class({
        'enableRateLimit': True,
        'timeout': 10000,
        'options': {'defaultType': 'future'}
    })
    
    try:
        markets = exchange.load_markets()
        print(f"SUCCESS {ex_id}: Found {len(markets)} markets")
    except Exception as e:
        print(f"FAILED {ex_id}: {type(e).__name__} - {str(e)}")
