import os
import json
from datetime import datetime

import logging
from ttf_logger import debug_logger

import alpaca_trade_api as trade_api

# ALPACA ACCESS (ENVIRONMENT VARIABLES)
API_KEY = os.environ.get('ALPACA_API')
API_SECRET = os.environ.get('ALPACA_SECRET')
WATCHLIST_ID = os.environ.get('ALPACA_WATCHLIST_ID')

# ALPACA URLs
PAPER_URL = 'https://paper-api.alpaca.markets'
DATA_URL = 'https://data.alpaca.markets'

api = trade_api.REST(API_KEY, API_SECRET, PAPER_URL)

def get_watchlist_symbols():
    
    watchlist = api.get_watchlist(WATCHLIST_ID)
        
    debug_logger.debug("API called for watchlist")

    watchlist_symbols = {asset['symbol'] for asset in watchlist.assets}
    
    return watchlist_symbols


def get_positions_symbols():
    
    positions = api.list_positions()
    
    debug_logger.debug("API called for positions")

    positions_symbols = {asset['symbol'] for asset in positions}
    
    return positions_symbols


def get_open_position(symbol):

    return api.get_position(symbol)._raw


def get_bars(symbol, timeframe, limit):

    return api.get_barset(symbol, timeframe, limit)[symbol]._raw

def place_order(symbol, side, qty, type='stop_limit', 
                time_in_force='gtc', order_class='bracket'):
    
    if is_tradable(symbol):
        
        stop, limit, take, loss = stop_limit_take_loss(symbol)
        
        api.submit_order(
            symbol=symbol,
            side=side,
            qty=str(qty),
            type=type,
            time_in_force=time_in_force,
            order_class=order_class,
            stop_price=stop,
            limit_price=limit,
            take_profit=take,
            stop_loss=loss
            )
    
    debug_logger.debug("""API called to place order for '{}'""".format(symbol))


def close_position(symbol):

    api.close_position(symbol)

    debug_logger.debug("""API called to close position for '{}'""".format(symbol))


def is_tradable(symbol):
    
    asset = api.get_asset(symbol)

    debug_logger.debug("""API called by is_tradable() for '{}'""".format(symbol))

    if (asset.status == 'active' and
        asset.tradable == True):
        return True
    else:
        return False


# Calculate take-profit and stop-loss order prices based on last quote
def stop_limit_take_loss(symbol):

    last_bar = api.get_barset(symbol, '1Min', limit=1)[symbol]
    last_close = last_bar[0].c
    
    stop_price = str(round(last_close * 0.98))
    limit_price = str(round(last_close * 1.04))
    take_profit = {
                    'limit_price': str(round(last_close * 1.25, 2))
                    }
    stop_loss = {
                'stop_price': str(round(last_close * 0.9, 2)),
                'limit_price': str(round(last_close * 0.88, 2))
                }
    
    return stop_price, limit_price, take_profit, stop_loss