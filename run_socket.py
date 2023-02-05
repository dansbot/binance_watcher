import asyncio
from binance import AsyncClient, BinanceSocketManager
from binance.client import Client
import logging
import os
import sys
import threading
from typing import Optional

log = logging.getLogger()
LOG_FORMATTER = logging.Formatter('%(asctime)s\t%(name)s\t%(filename)s:%(lineno)d\t%(levelname)s\t%(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMATTER)
log.addHandler(console_handler)
log.setLevel(logging.INFO)


def _kline_catch_up(symbol_pair: str) -> None:
    import database as db  # must import inside thread

    client = Client(api_key=os.environ.get("BINANCE_API_KEY"), api_secret=os.environ.get("BINANCE_API_SECRET"), tld='us')
    klines = client.get_klines(symbol=symbol_pair, interval='1m', limit=6000)
    log.info(f"Adding {len(klines)} klines to {symbol_pair}")
    db.add_multiple_klines(symbol_pair, '1m', klines, update=False)


def kline_catch_up(symbol_pair: str) -> None:
    threading.Thread(target=_kline_catch_up, args=(symbol_pair,)).start()


def _trade_catch_up(symbol_pair: str) -> None:
    import database as db  # must import inside thread

    client = Client(api_key=os.environ.get("BINANCE_API_KEY"), api_secret=os.environ.get("BINANCE_API_SECRET"), tld='us')
    trades = client.get_historical_trades(symbol=symbol_pair, limit=3000)
    log.info(f"Adding {len(trades)} trades to {symbol_pair}")
    db.add_multiple_trades(symbol_pair, trades, update=False)


def trade_catch_up(symbol_pair: str) -> None:
    threading.Thread(target=_trade_catch_up, args=(symbol_pair,)).start()


async def run_socket(symbol_pair: Optional[str], socket: Optional[str]):
    """
    :param symbol_pair: ex. BTCUSDT not BTC
    """
    import database as db  # must import inside thread

    log.info(f'Running. symbol: {symbol_pair}, socket: {socket}')
    client = await AsyncClient.create(api_key=os.environ.get("BINANCE_API_KEY"), api_secret=os.environ.get("BINANCE_API_SECRET"), tld='us')
    bm = BinanceSocketManager(client)
    # start any sockets here, i.e a trade socket
    if socket == 'kline':
        kline_catch_up(symbol_pair)
        ts = bm.kline_socket(symbol_pair)
    elif socket == 'trade':
        trade_catch_up(symbol_pair)
        ts = bm.trade_socket(symbol_pair)
    else:
        ts = bm.ticker_socket()
    # then start receiving messages
    async with ts as tscm:
        while True:
            res = await tscm.recv()
            log.info(res)
            if socket == 'kline':
                db.add_kline(res['k'])
            elif socket == 'trade':
                db.add_trade(res)
            await client.close_connection()


def start_loop(symbol_pair: str, socket: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_socket(symbol_pair, socket))
    loop.close()


def start_socket(symbol_pair: str, socket: str) -> threading.Thread:
    t = threading.Thread(target=start_loop, args=(symbol_pair, socket))
    t.start()
    return t


if __name__ == "__main__":
    try:
        symbol = sys.argv[1]
    except IndexError:
        symbol = None
        skt = None
    if symbol is not None:
        try:
            skt = sys.argv[2]
        except IndexError:
            skt = 'kline'
    start_loop(symbol, skt)
