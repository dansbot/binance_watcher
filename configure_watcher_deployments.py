from binance.client import Client
from copy import deepcopy
import os
import yaml

client = Client(
    api_key=os.environ.get("BINANCE_API_KEY"),
    api_secret=os.environ.get("BINANCE_API_SECRET"),
    tld='us',
)

with open('k8s/templates/watcher-deployment-template.yaml') as fp:
    deployment_template = yaml.safe_load(fp)

pairs = []
exchange_info = client.get_exchange_info()
for asset in exchange_info['symbols']:
    symbol = asset['symbol']
    if 'usd' not in symbol.lower():
        continue
    candles = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_3DAY)
    num_trades = 0
    for c in candles:
        num_trades += c[8]
    pairs.append((num_trades, symbol))
pairs.sort(reverse=True)
s = ""
for _, symbol in pairs[:100]:
    dep = deepcopy(deployment_template)
    dep['metadata']['name'] = symbol.lower()
    dep['spec']['template']['spec']['containers'][0]['args'] = [symbol, 'trade']
    s += yaml.dump(dep)
    s += "---\n"
    # break

with open('k8s/watcher-deployments.yaml', 'w') as fp:
    fp.write(s[:-len("---\n")])
print("complete")
