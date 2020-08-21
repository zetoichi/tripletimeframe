import json
from datetime import datetime

from stock_data import Stock

positions_file = 'ttf_records/open_positions.json'
trades_file = 'ttf_records/trades.json'

def store_open_positions(bought):
    """
    - get position record for each stock in 'bought'
    - append to list
    - load to json
    """
    global positions_file

    positions = [stock.position_record for stock in bought]

    with open(positions_file, 'w') as f:

        json.dump(positions, f, indent=4)


def store_new_trades(new_trades):

    global trades_file

    with open(trades_file, 'r') as f:

        trades = json.load(f)

    trades += new_trades

    with open(trades_file, 'w') as f:

        json.dump(trades, f, indent=4)


def get_open_positions():

    global positions_file
    
    with open(positions_file, 'r') as f:

        positions_list = json.load(f)
    
    return stocks_from_positions_list(positions_list)
    

def stocks_from_positions_list(positions_list):

    open_positions = set()

    for position in positions_list:
        for symbol in position.keys():
            
            stock = Stock(symbol, open=True)
            open_positions.add(stock)
    
    return open_positions