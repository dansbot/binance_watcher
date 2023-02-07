from datetime import datetime
import logging
import os
import psycopg2
from typing import Any, Dict, Iterable, List, Tuple, Union

log = logging.getLogger()

db_user = os.environ.get('POSTGRES_USER', 'postgres')
db_pwd = os.environ.get('POSTGRES_PASSWORD', 'kline')
db_host = os.environ.get('POSTGRES_HOST', 'localhost')
db_port = os.environ.get('POSTGRES_PORT', '5432')
db_name = os.environ.get('POSTGRES_DB', 'kline')

db_conn_string = f'postgresql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}'
db_conn_string = 'postgresql://postgres:kline@localhost:5432/kline'
print(f"Db connection string: {db_conn_string}")
conn = psycopg2.connect(db_conn_string)
cur = conn.cursor()
log.debug(f"Db connection set: {db_conn_string}")

tables = set()

KLINE_COLUMNS = 'start_time BIGINT PRIMARY KEY, end_time BIGINT, first_trade_id INTEGER, last_trade_id INTEGER, ' \
                'open FLOAT, close FLOAT, high FLOAT, low FLOAT, volume FLOAT, ' \
                'number_of_trades INTEGER, final_bar BOOL, ' \
                'quote_volume FLOAT, volume_of_active_buy FLOAT, quote_volume_of_active_buy FLOAT'

KLINE_COLUMNS_LIST = 'start_time, end_time, first_trade_id, last_trade_id, ' \
                     'open, close, high, low, volume, ' \
                     'number_of_trades, final_bar, ' \
                     'quote_volume, volume_of_active_buy, quote_volume_of_active_buy'

KLINE_KEYS = ["t", "T", "f", "L", "o", "c", "h", "l", "v", "n", "x", "q", "V", "Q"]

KLINE_EXCLUDED = 'EXCLUDED.'
for k in KLINE_COLUMNS_LIST.replace(',', '').split():
    KLINE_EXCLUDED += k + ", EXCLUDED."
KLINE_EXCLUDED = KLINE_EXCLUDED[: -len(", EXCLUDED.")]

TRADE_COLUMNS = 'event_time BIGINT PRIMARY KEY, trade_id INTEGER, price FLOAT, quantity FLOAT, buyer_order_id INTEGER, ' \
                'seller_order_id INTEGER, trade_time BIGINT, maker BOOLEAN'

TRADE_COLUMNS_LIST = 'event_time, trade_id, price, quantity, buyer_order_id, seller_order_id, trade_time, maker'

TRADE_KEYS = ["E", "t", "p", "q", "b", "a", "T", "m"]

TRADE_EXCLUDED = 'EXCLUDED.'
for k in TRADE_COLUMNS_LIST.replace(',', '').split():
    TRADE_EXCLUDED += k + ", EXCLUDED."
TRADE_EXCLUDED = TRADE_EXCLUDED[: -len(", EXCLUDED.")]


def execute_command(cmd: str, *args, fetch_func: str = None):
    try:
        log.debug(cmd)
        cur.execute(cmd, *args)
        if fetch_func:
            if fetch_func == 'fetchall':
                return cur.fetchall()
            elif fetch_func == 'fetchone':
                return cur.fetchone()
            elif fetch_func == 'fetchmany':
                return cur.fetchmany()
        conn.commit()
    except:
        log.critical(cmd, exc_info=True)
        raise


def format_table_name(table_name: str) -> str:
    try:
        int(table_name[0])
        return 'num_' + table_name
    except:
        return table_name


def update_tables():
    global tables
    cmd = "SELECT relname FROM pg_class WHERE relkind='r' AND relname !~ '^(pg_|sql_)';"
    _tables = execute_command(cmd, fetch_func='fetchall')
    tables = set(x[0] for x in _tables)


def get_all_rows(table_name: str, desc: bool = False) -> list:
    table_name = format_table_name(table_name)
    order_by = 'start_time' if not table_name.endswith('trade') else 'trade_time'
    sql = f'SELECT * FROM {table_name}'
    if order_by:
        sql += f' ORDER BY {order_by}'
        if desc:
            sql += ' DESC'
    return execute_command(sql, fetch_func='fetchall')


def get_latest_rows(table_name: str, limit: int = 1, asc: bool = False) -> tuple:
    table_name = format_table_name(table_name)
    order_by = 'start_time' if not table_name.endswith('trade') else 'trade_time'
    sql = f'SELECT * FROM {table_name} ORDER BY {order_by} DESC LIMIT {limit}'
    if asc:
        sql = f'SELECT * FROM ({sql}) AS t ORDER BY {order_by} ASC'
    return execute_command(sql, fetch_func='fetchall')


def get_rows_in_range(table_name: str, start_time: Union[int, datetime], end_time: Union[int, datetime]) -> tuple:
    """
    :param start_time: if integer, must be in same format at int(datetime.timestamp(datetime.utcnow()) * 1000)
                       if datetime, must have a utc timezone.
    :param end_time: if integer, must be in same format at int(datetime.timestamp(datetime.utcnow()) * 1000)
                     if datetime, must have a utc timezone.
    """
    table_name = format_table_name(table_name)
    order_by = 'start_time' if not table_name.endswith('trade') else 'trade_time'
    if isinstance(start_time, datetime):
        epoch = datetime(1970, 1, 1)
        start_time = int((start_time - epoch).total_seconds() * 1000)
    if isinstance(end_time, datetime):
        epoch = datetime(1970, 1, 1)
        end_time = int((end_time - epoch).total_seconds() * 1000)
    sql = f'SELECT * FROM {table_name} WHERE {order_by} BETWEEN {start_time} AND {end_time} ORDER BY {order_by} ASC'
    return execute_command(sql, fetch_func='fetchall')


def create_table(table_name: str, columns: str) -> None:
    table_name = format_table_name(table_name)
    cmd = f'CREATE TABLE IF NOT EXISTS ' \
          f'{table_name}({columns})'
    execute_command(cmd)
    update_tables()


def delete_table(table_name: str, not_exists_okay: bool = False) -> None:
    table_name = format_table_name(table_name)
    if table_name not in tables and not_exists_okay:
        return
    execute_command(f'DROP TABLE {table_name}')
    update_tables()


def add_kline(k: dict, update: bool = True) -> None:
    """
    "k": {
            "t": 1499404860000, 		# start time of this bar
            "T": 1499404919999, 		# end time of this bar
            "s": "ETHBTC",				# symbol
            "i": "1m",					# interval
            "f": 77462,					# first trade id
            "L": 77465,					# last trade id
            "o": "0.10278577",			# open
            "c": "0.10278645",			# close
            "h": "0.10278712",			# high
            "l": "0.10278518",			# low
            "v": "17.47929838",			# volume
            "n": 4,						# number of trades
            "x": false,					# whether this bar is final
            "q": "1.79662878",			# quote volume
            "V": "2.34879839",			# volume of active buy
            "Q": "0.24142166",			# quote volume of active buy
            "B": "13279784.01349473"	# can be ignored
        }
    """
    table_name = format_table_name(f"{k['s']}_{k['i']}".lower())
    if table_name not in tables:
        create_table(table_name=table_name, columns=KLINE_COLUMNS)

    vals = tuple([k[x] for x in KLINE_KEYS])
    # print(vals)
    sql = f"INSERT INTO {table_name} ({KLINE_COLUMNS_LIST}) VALUES{vals}"
    if update:
        sql += f' ON CONFLICT (start_time) DO UPDATE SET ({KLINE_COLUMNS_LIST}) = ({KLINE_EXCLUDED})'
    else:
        sql += f' ON CONFLICT (start_time) DO NOTHING'
    execute_command(sql, vals)


def add_multiple_klines(symbol: str, interval: str, klines: List[List[Any]], update: bool = False) -> None:
    klines = format_historical_klines(symbol, interval, klines)
    for chunk in chunks(klines):
        for kline in chunk:
            add_kline(kline, update=update)


def format_historical_klines(symbol: str, interval: str, klines: List[List[Any]]) -> List[Dict[str, Any]]:
    """
    [
        0: 1499040000000,      # Open time
        1: "0.01634790",       # Open
        2: "0.80000000",       # High
        3: "0.01575800",       # Low
        4: "0.01577100",       # Close
        5: "148976.11427815",  # Volume
        6: 1499644799999,      # Close time
        7: "2434.19055334",    # Quote asset volume
        8: 308,                # Number of trades
        9: "1756.87402397",    # Taker buy base asset volume
        10: "28.46694368",      # Taker buy quote asset volume
        11: "17928899.62484339" # Can be ignored
    ]
    """
    formatted = []
    for l in klines:
        r = {"t": l[0], "T": l[6], "f": -1, "L": -1, "o": l[1], "c": l[4], "h": l[2], "l": l[3], "v": l[5], "n": l[8], "x": True, "q": l[7], "V": l[9], "Q": l[10]}
        r['s'] = symbol
        r['i'] = interval
        formatted.append(r)
    return formatted


def add_trade(t: dict, update: bool = True) -> None:
    """
    t = {
          "e": "trade",     // Event type
          "E": 123456789,   // Event time
          "s": "BNBBTC",    // Symbol
          "t": 12345,       // Trade ID
          "p": "0.001",     // Price
          "q": "100",       // Quantity
          "b": 88,          // Buyer order ID
          "a": 50,          // Seller order ID
          "T": 123456785,   // Trade time
          "m": true,        // Is the buyer the market maker?
          "M": true         // Ignore
        }
    """
    table_name = format_table_name(f"{t['s']}_trade".lower())
    if table_name not in tables:
        create_table(table_name=table_name, columns=TRADE_COLUMNS)

    vals = tuple([t[x] for x in TRADE_KEYS])
    # print(vals)
    sql = f"INSERT INTO {table_name} ({TRADE_COLUMNS_LIST}) VALUES{vals}"
    if update:
        sql += f' ON CONFLICT (event_time) DO UPDATE SET ({TRADE_COLUMNS_LIST}) = ({TRADE_EXCLUDED})'
    else:
        sql += f' ON CONFLICT (event_time) DO NOTHING'
    execute_command(sql, vals)


def add_multiple_trades(symbol: str,  trades: List[dict], update: bool = False) -> None:
    table_name = format_table_name(f"{symbol}_trade".lower())
    if table_name not in tables:
        create_table(table_name=table_name, columns=TRADE_COLUMNS)
    generator = yield_trades(trades)
    while 1:
        try:
            vals = ''
            chunk = next(generator)
            if not chunk:
                break
            for t in chunk:
                vals += f"({','.join([str(x) for x in t])}),"
            sql = f"INSERT INTO {table_name} ({TRADE_COLUMNS_LIST}) VALUES{vals[:-1]}"
            if update:
                sql += f' ON CONFLICT (event_time) DO UPDATE SET ({TRADE_COLUMNS_LIST}) = ({TRADE_EXCLUDED})'
            else:
                sql += f' ON CONFLICT (event_time) DO NOTHING'
            execute_command(sql, chunk)
        except StopIteration:
            break


def yield_trades(trades: List[dict]) -> Iterable[List[Tuple[int, int, float, float, int, int, int, bool]]]:
    stack = []
    i = 0
    while i < len(trades):
        t = trades[i]
        if 'isBuyerMaker' in t:
            t = {"E": t['time'], "t": t['id'], "p": t['price'], "q": t['qty'], "b": -1, "a": -1, "T": -1, "m": t['isBuyerMaker']}
        vals = tuple([t[x] for x in TRADE_KEYS])
        stack.append(vals)
        if len(stack) == 1000:
            yield stack
            stack.clear()
        i += 1
    if stack:
        yield stack


def format_historical_trades(symbol: str, trades: List[dict]) -> List[Dict[str, Any]]:
    """
    Trade websocket |  hist. trades  | description
                "E" |     "time"     | Event time
                "t" |      "id"      | Trade ID
                "p" |     "price"    | Price
                "q" |      "qty"     | Quantity
                "b" |      null      | Buyer order ID
                "a" |      null      | Seller order ID
                "T" |      null      | Trade time
                "m" | "isBuyerMaker" | Is the buyer the market maker?
        }

    {'e': 'trade', 'E': 1638744145033, 's': 'ATOMUSDT', 't': 1905706, 'p': '24.12400000', 'q': '1.21300000', 'b': 93501871, 'a': 93506230, 'T': 1638744145033, 'm': True, 'M': True}
    {'id': 1905706, 'price': '24.12400000', 'qty': '1.21300000', 'quoteQty': '29.26241200', 'time': 1638744145033, 'isBuyerMaker': True, 'isBestMatch': True}
    """
    formatted = []
    for t in trades:
        r = {"E": t['time'], "t": t['id'], "p": t['price'], "q": t['qty'], "b": -1, "a": -1, "T": -1, "m": t['isBuyerMaker']}
        r['s'] = symbol
        formatted.append(r)
    return formatted


def chunks(data, rows=1000):
    """ Divides the data into 1000 rows each """
    for i in range(0, len(data), rows):
        yield data[i:i + rows]


update_tables()

if __name__ == '__main__':
    log.setLevel(logging.DEBUG)
    tbls = []
    for table in tables:
        if table.startswith('charlie'):
            delete_table(table)
        elif table.endswith('trade'):
            rows = get_all_rows(table)
            if rows:
                tbls.append((datetime.utcfromtimestamp(rows[0][0] / 1000), len(rows), table))
    tbls.sort()

    for t in tbls:
        print(t)
