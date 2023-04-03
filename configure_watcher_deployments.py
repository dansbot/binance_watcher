import argparse
import os
import sys
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

import yaml
from binance.client import Client

# Load the deployment template from a YAML file
with open("k8s/templates/watcher-deployment-template.yaml") as fp:
    DEPLOYMENT_TEMPLATE = yaml.safe_load(fp)


def get_exchange_info(client: Optional[Client] = None) -> Dict:
    if client is None:
        # Create a client instance using the Binance API key and secret
        client = Client(
            api_key=os.environ.get("BINANCE_API_KEY"),
            api_secret=os.environ.get("BINANCE_API_SECRET"),
            tld="us",
        )
    return client.get_exchange_info()


def get_symbols(args: argparse.Namespace):
    # Create a client instance using the Binance API key and secret
    client = Client(
        api_key=os.environ.get("BINANCE_API_KEY"),
        api_secret=os.environ.get("BINANCE_API_SECRET"),
        tld="us",
    )
    # Get the list of asset pairs from the exchange info
    pairs = []
    print("Retrieving list of symbols from Binance-US")
    exchange_info = get_exchange_info(client)
    for asset in exchange_info["symbols"]:
        symbol = asset["symbol"]
        # Filter out pairs that do not include USD
        if "usd" not in symbol.lower():
            continue
        num_trades = 0
        if args.rank_by_num_trades:
            # Get the number of trades for the symbol over the last 150 days
            candles = client.get_klines(
                symbol=symbol, interval=Client.KLINE_INTERVAL_3DAY
            )
            for c in candles:
                num_trades += c[8]
        pairs.append((num_trades, symbol))

    # Sort the pairs by the number of trades if the rank flag is present
    if args.rank_by_num_trades:
        print("Ranking by number of trades.")
        pairs.sort(reverse=True)

    if args.limit:
        return pairs[: args.limit]
    return pairs


def write_deployment_yamls(pairs: List):
    # Create a YAML string of the deployments, using the template and symbol information
    s = ""
    for x in pairs:
        if isinstance(x, tuple):
            _, symbol = x
        else:
            symbol = x
        dep = deepcopy(DEPLOYMENT_TEMPLATE)
        dep["metadata"]["name"] = symbol.lower()
        dep["spec"]["template"]["spec"]["containers"][0]["args"] = [symbol, "trade"]
        s += yaml.dump(dep)
        s += "---\n"

    # Write the YAML string to a file
    with open("k8s/watcher-deployments.yaml", "w") as fp:
        fp.write(s[: -len("---\n")])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
    )
    parser.add_argument(
        "-rnt",
        "--rank_by_num_trades",
        help="Rank by number of trades",
        action="store_true",
    )
    parser.add_argument(
        "-lmt",
        "--limit",
        help="Limit the number of symbols to write deployments for.",
    )
    parser.add_argument(
        "-s", "--symbols", help="List of symbols to write deployments for.", nargs="+"
    )
    args = parser.parse_args()

    if args.symbols:
        write_deployment_yamls(args.symbols)
    else:
        pairs = get_symbols(args)
        write_deployment_yamls(pairs)

    # Print a message indicating the script is complete
    print("complete")
