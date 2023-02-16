"""
This script initializes the database connection and creates a cursor object for executing SQL commands.

It sets the environment variables for the Postgres database if not already set and uses the values to create the connection string.
It connects to the Postgres database using the connection string and creates a cursor object.

"""

from datetime import datetime
import logging
import os
import psycopg2
from typing import Any, Dict, Iterable, List, Tuple, Union

log = logging.getLogger()

# Set the default values for the environment variables and get them if already set.
db_user = os.environ.get('POSTGRES_USER', 'postgres')
db_pwd = os.environ.get('POSTGRES_PASSWORD', 'root')
db_host = os.environ.get('POSTGRES_HOST', 'localhost')
db_port = os.environ.get('POSTGRES_PORT', '5432')
db_name = os.environ.get('POSTGRES_DB', 'postgresdb')

# Create the connection string for the Postgres database
db_conn_string = f'postgresql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}'
log.debug(f"Db connection string: {db_conn_string}")

# Create the connection and cursor objects
conn = psycopg2.connect(db_conn_string)
cur = conn.cursor()
log.debug(f"Db connection set: {db_conn_string}")

# Define an empty set to store table names
tables = set()

# Define column names for the Kline table
KLINE_COLUMNS = 'start_time BIGINT PRIMARY KEY, end_time BIGINT, first_trade_id INTEGER, last_trade_id INTEGER, ' \
                'open FLOAT, close FLOAT, high FLOAT, low FLOAT, volume FLOAT, ' \
                'number_of_trades INTEGER, final_bar BOOL, ' \
                'quote_volume FLOAT, volume_of_active_buy FLOAT, quote_volume_of_active_buy FLOAT'

# Define a comma-separated list of column names for the Kline table
KLINE_COLUMNS_LIST = 'start_time, end_time, first_trade_id, last_trade_id, ' \
                     'open, close, high, low, volume, ' \
                     'number_of_trades, final_bar, ' \
                     'quote_volume, volume_of_active_buy, quote_volume_of_active_buy'

# Define a list of keys for Kline data
KLINE_KEYS = ["t", "T", "f", "L", "o", "c", "h", "l", "v", "n", "x", "q", "V", "Q"]

# Define a string that will be used to exclude columns in a Kline table upsert
KLINE_EXCLUDED = 'EXCLUDED.'
for k in KLINE_COLUMNS_LIST.replace(',', '').split():
    # Append the current column name and ", EXCLUDED." to the KLINE_EXCLUDED string
    KLINE_EXCLUDED += k + ", EXCLUDED."
KLINE_EXCLUDED = KLINE_EXCLUDED[: -len(", EXCLUDED.")]

# Define column names for the Trade table
TRADE_COLUMNS = 'event_time BIGINT PRIMARY KEY, trade_id INTEGER, price FLOAT, quantity FLOAT, buyer_order_id INTEGER, ' \
                'seller_order_id INTEGER, trade_time BIGINT, maker BOOLEAN'

# Define a comma-separated list of column names for the Trade table
TRADE_COLUMNS_LIST = 'event_time, trade_id, price, quantity, buyer_order_id, seller_order_id, trade_time, maker'

# Define a list of keys for Trade data
TRADE_KEYS = ["E", "t", "p", "q", "b", "a", "T", "m"]

# Define a string that will be used to exclude columns in a Trade table upsert
TRADE_EXCLUDED = 'EXCLUDED.'
for k in TRADE_COLUMNS_LIST.replace(',', '').split():
    # Append the current column name and ", EXCLUDED." to the TRADE_EXCLUDED string
    TRADE_EXCLUDED += k + ", EXCLUDED."
TRADE_EXCLUDED = TRADE_EXCLUDED[: -len(", EXCLUDED.")]


def execute_command(cmd: str, *args, fetch_func: str = None) -> Union[List[Tuple], Tuple, None]:
    """
    Executes a given SQL command using the cursor object 'cur', and commits the transaction.
    If a fetch function is specified, the result of the fetch is returned, otherwise None is returned.

    :param cmd: str, SQL command to be executed
    :param args: optional arguments to be used with the SQL command
    :param fetch_func: str, optional fetch function to be used. Must be one of 'fetchall', 'fetchone', 'fetchmany', or None.

    :return: Union[List[Tuple], Tuple, None], if a fetch function is provided, its output is returned, otherwise None is returned.
    """
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
    """
    Formats the table name by adding the prefix 'num_' if the table name starts with a number.
    This is because table names in SQL cannot start with a number.

    :param table_name: str, name of the table to be formatted

    :return: str, formatted table name
    """
    try:
        int(table_name[0])
        return 'num_' + table_name
    except:
        return table_name


def update_tables():
    """
    Updates the global variable `tables` with the names of all tables in the connected PostgreSQL database.
    """
    global tables
    cmd = "SELECT relname FROM pg_class WHERE relkind='r' AND relname !~ '^(pg_|sql_)';"
    _tables = execute_command(cmd, fetch_func='fetchall')
    tables = set(x[0] for x in _tables)


def get_all_rows(table_name: str, desc: bool = False) -> List[Tuple]:
    """
    Returns all rows in the specified table as a list of tuples, ordered by 'start_time' (if the table is a klines table)
    or 'trade_time' (if the table is a trades table).

    :param table_name: str, name of the table to retrieve rows from
    :param desc: bool, whether to order the rows in descending order (default: False)

    :return: List[Tuple], list of tuples where each tuple represents a row in the specified table
    """
    table_name = format_table_name(table_name)
    order_by = 'start_time' if not table_name.endswith('trade') else 'trade_time'
    sql = f'SELECT * FROM {table_name}'
    if order_by:
        sql += f' ORDER BY {order_by}'
        if desc:
            sql += ' DESC'
    return execute_command(sql, fetch_func='fetchall')


def get_latest_rows(table_name: str, limit: int = 1, asc: bool = False) -> tuple:
    """
    Get the latest rows from a specified table.

    :param table_name: A string representing the name of the table to retrieve rows from.
    :param limit: An integer representing the maximum number of rows to retrieve. Default is 1.
    :param asc: A boolean indicating whether the rows should be returned in ascending order. Default is False.
    :return: A tuple containing the retrieved rows from the table.
    """
    table_name = format_table_name(table_name)
    order_by = 'start_time' if not table_name.endswith('trade') else 'trade_time'
    sql = f'SELECT * FROM {table_name} ORDER BY {order_by} DESC LIMIT {limit}'
    if asc:
        sql = f'SELECT * FROM ({sql}) AS t ORDER BY {order_by} ASC'
    return execute_command(sql, fetch_func='fetchall')


def get_rows_in_range(table_name: str, start_time: Union[int, datetime], end_time: Union[int, datetime]) -> tuple:
    """
    Retrieves rows from a specified table between a specified start and end time, sorted by time in ascending order.

    :param table_name: Name of the table to query.
    :param start_time: Start time of the range to query. If integer, must be in same format as
                       int(datetime.timestamp(datetime.utcnow()) * 1000). If datetime, must have a utc timezone.
    :param end_time: End time of the range to query. If integer, must be in same format as
                     int(datetime.timestamp(datetime.utcnow()) * 1000). If datetime, must have a utc timezone.

    :return: A tuple containing the retrieved rows.
    """
    table_name = format_table_name(table_name)
    # Check if the table ends with 'trade', if it does, order by 'trade_time', otherwise order by 'start_time'
    order_by = 'start_time' if not table_name.endswith('trade') else 'trade_time'
    # If start_time is datetime object, convert it to integer timestamp format
    if isinstance(start_time, datetime):
        epoch = datetime(1970, 1, 1)
        start_time = int((start_time - epoch).total_seconds() * 1000)
    # If end_time is datetime object, convert it to integer timestamp format
    if isinstance(end_time, datetime):
        epoch = datetime(1970, 1, 1)
        end_time = int((end_time - epoch).total_seconds() * 1000)
    # Construct the SQL query with the table name, start and end times, and order by clause
    sql = f'SELECT * FROM {table_name} WHERE {order_by} BETWEEN {start_time} AND {end_time} ORDER BY {order_by} ASC'
    # Execute the SQL query and return the result as a tuple
    return execute_command(sql, fetch_func='fetchall')


def create_table(table_name: str, columns: str) -> None:
    """
    Create a new table in the database if it does not exist already.

    :param table_name: A string name for the new table
    :param columns: A string containing the column definitions for the new table
    """
    # Format table name
    table_name = format_table_name(table_name)
    # Create the SQL command for table creation
    cmd = f'CREATE TABLE IF NOT EXISTS {table_name}({columns})'
    # Execute the SQL command
    execute_command(cmd)
    # Update the list of table names
    update_tables()


def delete_table(table_name: str, not_exists_okay: bool = False) -> None:
    """
    Delete a table from the database.

    :param table_name: A string name of the table to be deleted
    :param not_exists_okay: A boolean indicating whether to ignore if the table does not exist already.
    """
    # Format table name
    table_name = format_table_name(table_name)
    # If table does not exist and not_exists_okay is True, just return
    if table_name not in tables and not_exists_okay:
        return
    # Create the SQL command for table deletion
    execute_command(f'DROP TABLE {table_name}')
    # Update the list of table names
    update_tables()


def add_kline(k: dict, update: bool = True) -> None:
    """
    This function adds a k-line (candlestick) to a PostgreSQL database table.
    The k-line data is passed in as a dictionary, and the update parameter
    determines whether the function updates existing data or not.

    :Example Inputs:
    k = {
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

    :param k: A dictionary representing the k-line data.
    :param update: A boolean indicating whether to update existing data.
    """
    # Get the table name based on the symbol and interval in the k-line data
    table_name = format_table_name(f"{k['s']}_{k['i']}".lower())

    # If the table doesn't exist, create it with the appropriate columns
    if table_name not in tables:
        create_table(table_name=table_name, columns=KLINE_COLUMNS)

    # Extract the values from the k-line dictionary and create a tuple
    vals = tuple([k[x] for x in KLINE_KEYS])

    # Construct the SQL INSERT statement
    sql = f"INSERT INTO {table_name} ({KLINE_COLUMNS_LIST}) VALUES{vals}"

    # If update is True, add an ON CONFLICT clause to update existing data
    if update:
        sql += f' ON CONFLICT (start_time) DO UPDATE SET ({KLINE_COLUMNS_LIST}) = ({KLINE_EXCLUDED})'
    # If update is False, add an ON CONFLICT clause to do nothing
    else:
        sql += f' ON CONFLICT (start_time) DO NOTHING'

    # Execute the SQL command with the values tuple
    execute_command(sql, vals)


def add_multiple_klines(symbol: str, interval: str, klines: Dict, update: bool = False) -> None:
    """
    Inserts multiple klines into the appropriate table(s) in the database.

    Args:
        symbol (str): The trading symbol, e.g. 'BTCUSDT'.
        interval (str): The time interval of the klines, e.g. '1m' for 1 minute, '1h' for 1 hour.
        klines (List[List[Any]]): A list of klines in the following format:
            [
                [1499040000000, "0.01634790", "0.80000000", "0.01575800", "0.01577100", "148976.11427815", 1499644799999, "2434.19055334", 308, "1756.87402397", "28.46694368", "17928899.62484339"],
                [1499644800000, "0.01586000", "0.01615100", "0.01575800", "0.01589100", "177331.61767500", 1499731199999, "2827.64242383", 480, "1095.51108437", "17.47999999", "17815803.50348990"]
            ]
        update (bool): Whether to update existing klines in the table(s) or not. Defaults to False.

    Returns:
        None
    """
    klines = format_historical_klines(symbol, interval, klines)
    for chunk in chunks(klines):
        values = []
        for kline in chunk:
            vals = tuple([kline[x] for x in KLINE_KEYS])
            kline_values = ", ".join(str(value) for value in vals)
            values.append(f"({kline_values})")
        values_str = ", ".join(values)
        sql = f"INSERT INTO {symbol}_{interval} ({KLINE_COLUMNS_LIST}) VALUES {values_str}"
        # If update is True, add an ON CONFLICT clause to update existing data
        if update:
            sql += f' ON CONFLICT (start_time) DO UPDATE SET ({KLINE_COLUMNS_LIST}) = ({KLINE_EXCLUDED})'
        # If update is False, add an ON CONFLICT clause to do nothing
        else:
            sql += f' ON CONFLICT (start_time) DO NOTHING'
        execute_command(sql, values)


def format_historical_klines(symbol: str, interval: str, klines: List[List[Any]]) -> List[Dict[str, Any]]:
    """
    Formats historical klines into a list of dictionaries to match the format used in the database.

    :param symbol: The trading symbol, e.g. 'BTCUSDT'.
    :param interval: The time interval of the klines, e.g. '1m' for 1 minute, '1h' for 1 hour.
    :param klines : A list of klines in the following format:
            [
                [1499040000000, "0.01634790", "0.80000000", "0.01575800", "0.01577100", "148976.11427815", 1499644799999, "2434.19055334", 308, "1756.87402397", "28.46694368", "17928899.62484339"],
                [1499644800000, "0.01586000", "0.01615100", "0.01575800", "0.01589100", "177331.61767500", 1499731199999, "2827.64242383", 480, "1095.51108437", "17.47999999", "17815803.50348990"]
            ]

    :return:A list of dictionaries, where each dictionary represents a kline.
    """
    formatted = []
    for l in klines:
        # Construct a dictionary for each kline
        r = {
            's': symbol,  # symbol
            'i': interval,  # interval
            't': l[0],  # open time
            'T': l[6],  # close time
            'f': -1,  # first trade ID
            'L': -1,  # last trade ID
            'o': l[1],  # open price
            'c': l[4],  # close price
            'h': l[2],  # high price
            'l': l[3],  # low price
            'v': l[5],  # base asset volume
            'n': l[8],  # number of trades
            'x': True,  # whether this kline is final
            'q': l[7],  # quote asset volume
            'V': l[9],  # taker buy base asset volume
            'Q': l[10],  # taker buy quote asset volume
        }
        formatted.append(r)
    return formatted


def chunks(data, n_rows=1000):
    """
    Divides data into 1000 rows each
    """
    for i in range(0, len(data), n_rows):
        yield data[i:i + n_rows]


def add_trade(t: dict, update: bool = True) -> None:
    """
    Add a trade to the trades table in the database.

    :param t: A dictionary containing the trade information in the following format:
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
    :param update: Whether to update the row in case of a conflict.
        If True, the row will be updated with the new values, otherwise nothing
        will happen. Default is True.
    """

    # Construct the name of the trades table for the given symbol
    table_name = format_table_name(f"{t['s']}_trade".lower())

    # Create the trades table if it does not already exist
    if table_name not in tables:
        create_table(table_name=table_name, columns=TRADE_COLUMNS)

    # Get the values for the trade from the dictionary
    vals = tuple([t[x] for x in TRADE_KEYS])

    # Construct the SQL query to insert the trade into the table
    sql = f"INSERT INTO {table_name} ({TRADE_COLUMNS_LIST}) VALUES{vals}"

    # Add ON CONFLICT clause to the SQL query
    if update:
        sql += f' ON CONFLICT (event_time) DO UPDATE SET ({TRADE_COLUMNS_LIST}) = ({TRADE_EXCLUDED})'
    else:
        sql += f' ON CONFLICT (event_time) DO NOTHING'

    # Execute the SQL query to add the trade to the table
    execute_command(sql, vals)


def add_multiple_trades(symbol: str, trades: List[dict], update: bool = False) -> None:
    """
    Add multiple trades to a table with the name format "{symbol}_trade".

    :param symbol: The trading pair symbol.
    :param trades: A list of dictionaries containing trade information.
    :param update: Whether to update the row if it already exists. Defaults to False.
    """
    table_name = format_table_name(f"{symbol}_trade".lower())
    if table_name not in tables:
        create_table(table_name=table_name, columns=TRADE_COLUMNS)

    # Split the trades into chunks of 1000 and insert them into the table one chunk at a time.
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
    """
    A generator that yields the trades in the correct format for the insert statement.

    Args:
        trades (List[dict]): A list of dictionaries containing trade information.

    Yields:
        Iterable[List[Tuple[int, int, float, float, int, int, int, bool]]]: A list of tuples containing trade information.
    """
    stack = []
    i = 0
    while i < len(trades):
        t = trades[i]
        # If the trade is in the correct format, use it. Otherwise, extract the necessary information from the dictionary.
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
    Takes in a symbol and a list of trade dictionaries from the Binance API and formats them to match the schema used in
    the database. The resulting formatted trade objects are stored in a list.

    Trade websocket |  hist. trades  | description
                "E" |     "time"     | Event time
                "t" |      "id"      | Trade ID
                "p" |     "price"    | Price
                "q" |      "qty"     | Quantity
                "b" |      null      | Buyer order ID
                "a" |      null      | Seller order ID
                "T" |      null      | Trade time
                "m" | "isBuyerMaker" | Is the buyer the market maker?

    :param symbol: A string representing the trading symbol of the trades.
    :param trades: A list of trade dictionaries from the Binance API.

    :returns: A list of trade dictionaries that have been formatted to match the schema used in the database.
    """
    formatted = []
    for t in trades:
        r = {"E": t['time'], "t": t['id'], "p": t['price'], "q": t['qty'], "b": -1, "a": -1, "T": -1, "m": t['isBuyerMaker']}
        r['s'] = symbol
        formatted.append(r)
    return formatted


# update tables on module import and script start
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
