from binance.client import Client
from copy import deepcopy
import os
import sys
import yaml

# Check if the rank flag is present in the arguments
rank_by_num_trades = "--rank" in sys.argv

# Create a client instance using the Binance API key and secret
client = Client(
    api_key=os.environ.get("BINANCE_API_KEY"),
    api_secret=os.environ.get("BINANCE_API_SECRET"),
    tld='us',
)

# Load the deployment template from a YAML file
with open('k8s/templates/watcher-deployment-template.yaml') as fp:
    deployment_template = yaml.safe_load(fp)

# Get the list of asset pairs from the exchange info
pairs = []
print("Retrieving list of symbols from Binance-US")
exchange_info = client.get_exchange_info()
for asset in exchange_info['symbols']:
    symbol = asset['symbol']
    # Filter out pairs that do not include USD
    if 'usd' not in symbol.lower():
        continue
    num_trades = 0
    if rank_by_num_trades:
        # Get the number of trades for the symbol over the last 150 days
        candles = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_3DAY)
        for c in candles:
            num_trades += c[8]
    pairs.append((num_trades, symbol))

# Sort the pairs by the number of trades if the rank flag is present
if rank_by_num_trades:
    print('Ranking by number of trades.')
    pairs.sort(reverse=True)

# Get the limit from the arguments, or use the full length of the list if not specified
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else len(pairs)

# Create a YAML string of the deployments, using the template and symbol information
s = ""
for _, symbol in pairs[:limit]:
    dep = deepcopy(deployment_template)
    dep['metadata']['name'] = symbol.lower()
    dep['spec']['template']['spec']['containers'][0]['args'] = [symbol, 'trade']
    s += yaml.dump(dep)
    s += "---\n"

# Write the YAML string to a file
with open('k8s/watcher-deployments.yaml', 'w') as fp:
    fp.write(s[:-len("---\n")])

# Print a message indicating the script is complete
print("complete")
