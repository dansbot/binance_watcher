import asyncio
from binance import AsyncClient, BinanceSocketManager
from binance.client import Client
import logging
import os
import threading
from typing import Optional

# Set up logging object with console handler that prints log messages to console
log = logging.getLogger()
LOG_FORMATTER = logging.Formatter('%(asctime)s\t%(name)s\t%(filename)s:%(lineno)d\t%(levelname)s\t%(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMATTER)
log.addHandler(console_handler)
log.setLevel(logging.INFO)


def _kline_catch_up(symbol_pair: str) -> None:
    """
    Catch up on missing klines for the specified symbol pair and add them to the database.

    :param symbol_pair: The symbol pair to catch up on klines for.
    """
    import database as db  # must import inside thread

    # Connect to Binance API and get klines for the specified symbol pair
    client = Client(
        api_key=os.environ.get("BINANCE_API_KEY"),
        api_secret=os.environ.get("BINANCE_API_SECRET"),
        tld='us',
    )
    klines = client.get_klines(symbol=symbol_pair, interval='1m', limit=6000)

    # Log the number of klines being added to the database and add them to the database
    log.info(f"Adding {len(klines)} klines to {symbol_pair}")
    db.add_multiple_klines(symbol_pair, '1m', klines, update=False)


def kline_catch_up(symbol_pair: str) -> None:
    """
    Create a new thread to catch up on missing klines for the specified symbol pair and add them to the database.

    :param symbol_pair: The symbol pair to catch up on klines for.
    """
    # Start a new thread to catch up on klines for the specified symbol pair
    threading.Thread(target=_kline_catch_up, args=(symbol_pair,)).start()


def _trade_catch_up(symbol_pair: str) -> None:
    """
    Catch up on missing trades for the specified symbol pair and add them to the database.

    :param symbol_pair: The symbol pair to catch up on trades for.
    """
    import database as db  # must import inside thread

    # Connect to Binance API and get historical trades for the specified symbol pair
    client = Client(
        api_key=os.environ.get("BINANCE_API_KEY"),
        api_secret=os.environ.get("BINANCE_API_SECRET"),
        tld='us',
    )
    trades = client.get_historical_trades(symbol=symbol_pair, limit=3000)

    # Log the number of trades being added to the database and add them to the database
    log.info(f"Adding {len(trades)} trades to {symbol_pair}")
    db.add_multiple_trades(symbol_pair, trades, update=False)


def trade_catch_up(symbol_pair: str) -> None:
    """
    Create a new thread to catch up on missing trades for the specified symbol pair and add them to the database.

    :param symbol_pair: The symbol pair to catch up on trades for.
    """
    # Start a new thread to catch up on trades for the specified symbol pair
    threading.Thread(target=_trade_catch_up, args=(symbol_pair,)).start()


async def run_socket(symbol_pair: Optional[str], socket: Optional[str]):
    """
    Start a WebSocket connection to Binance and listen for incoming messages.

    :param symbol_pair: The trading pair symbol, e.g. BTCUSDT.
    :param socket: The type of WebSocket to start, either kline, trade, or ticker.
    """
    import database as db  # Import database module inside this function.

    log.info(f'Running. symbol: {symbol_pair}, socket: {socket}')

    # Create a new AsyncClient instance using the API key and secret in the environment variables.
    client = await AsyncClient.create(
        api_key=os.environ.get("BINANCE_API_KEY"),
        api_secret=os.environ.get("BINANCE_API_SECRET"),
        tld='us',
    )

    # Create a new BinanceSocketManager instance using the AsyncClient instance.
    bm = BinanceSocketManager(client)

    # Start the appropriate WebSocket connection based on the specified socket type.
    if socket == 'kline':
        kline_catch_up(symbol_pair)  # Perform any necessary catch-up actions for klines.
        ts = bm.kline_socket(symbol_pair)  # Start the kline socket.
    elif socket == 'trade':
        trade_catch_up(symbol_pair)  # Perform any necessary catch-up actions for trades.
        ts = bm.trade_socket(symbol_pair)  # Start the trade socket.
    else:
        ts = bm.ticker_socket()  # Start the ticker socket.

    # Begin listening for incoming messages on the WebSocket connection.
    async with ts as tscm:
        while True:
            res = await tscm.recv()  # Wait for an incoming message.
            log.info(res)  # Log the incoming message.
            if socket == 'kline':
                db.add_kline(res['k'])  # Add the kline to the database.
            elif socket == 'trade':
                db.add_trade(res)  # Add the trade to the database.

            # Close the WebSocket connection after each message is received.
            await client.close_connection()


def start_loop(symbol_pair: str, socket: str):
    """
    Starts a new event loop and runs a socket in that loop.

    :param symbol_pair: The symbol pair to create a socket for (e.g. 'BTCUSDT').
    :param socket: The type of socket to create (either 'kline', 'trade', or None for a ticker socket).
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_socket(symbol_pair, socket))
    loop.close()


def start_socket(symbol_pair: str, socket: str) -> threading.Thread:
    """
    Starts a new thread and runs a socket in that thread.

    :param symbol_pair: The symbol pair to create a socket for (e.g. 'BTCUSDT').
    :param socket: The type of socket to create (either 'kline', 'trade', or None for a ticker socket).
    :return: A threading.Thread object representing the new thread.
    """
    t = threading.Thread(target=start_loop, args=(symbol_pair, socket))
    t.start()
    return t


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
    )
    parser.add_argument(
        'symbol',
        help="Symbol to track",
    )
    parser.add_argument(
        'socket',
        help="Socket to attach to",
        type=str.lower,
        choices=['kline', 'trade']
    )
    parser.add_argument(
        '-l',
        '--log_level',
        help='Set the log level.',
        type=str.upper,
        choices=['CRITICAL', 'FATAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'],
        default="INFO",
    )
    args = parser.parse_args()
    log.setLevel(args.log_level)

    start_loop(args.symbol, args.socket)
