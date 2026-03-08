import ccxt

exchange = ccxt.gateio({
    'options': {'defaultType': 'future'}
})
exchange.load_markets()

swaps = 0
for symbol, m in exchange.markets.items():
    if m.get('quote') == 'USDT' and (m.get('swap', False) or m.get('linear', False) or m.get('type') == 'swap'):
        swaps += 1

print(f"Total markets: {len(exchange.markets)}")
print(f"Total USDT swaps/futures: {swaps}")

# Let's inspect the first swap market
for symbol, m in exchange.markets.items():
    if m.get('quote') == 'USDT' and (m.get('swap', False) or m.get('type') == 'swap'):
        print(f"Example Swap Market: {symbol}")
        print({k: m[k] for k in ['id', 'symbol', 'base', 'quote', 'type', 'swap', 'linear', 'contract'] if k in m})
        break
