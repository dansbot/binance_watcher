from binance.client import Client
from copy import deepcopy
import os
import yaml
from pprint import pprint

client = Client(
    api_key=os.environ.get("BINANCE_API_KEY"),
    api_secret=os.environ.get("BINANCE_API_SECRET"),
    tld='us',
)

with open('k8s/watcher-deployment-template.yaml') as fp:
    deployment_template = yaml.safe_load(fp)

s = ""
exchange_info = client.get_exchange_info()
for symbol in exchange_info['symbols']:
    dep = deepcopy(deployment_template)
    dep['spec']['template']['spec']['containers'][0]['args'] = [symbol['symbol'], 'trade']
    s += yaml.dump(dep)
    s += "---\n"

with open('k8s/watcher-deployments.yaml', 'w') as fp:
    fp.write(s[:-len("---\n")])
