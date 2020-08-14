import os
import json

import logging
from ttf_logger import debug_logger, error_logging

import requests
import pandas as pd
from requests import HTTPError

class Alpaca:
    
    # ALPACA ACCESS (ENVIRONMENT VARIABLES)
    api_key = os.environ.get('ALPACA_API')
    api_secret = os.environ.get('ALPACA_SECRET')
    watchlist_id = os.environ.get('ALPACA_WATCHLIST_ID')
    
    headers = {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': api_secret
        }

    # ALPACA URLs
    base_url = 'https://paper-api.alpaca.markets/v2'
    orders_url = base_url + '/orders'
    acct_url = base_url + '/account'
    watchlist_url = base_url + '/watchlists/' + str(watchlist_id)
    assets_url = base_url + '/assets/'
    positions_url = base_url + '/positions'
    
    market_url = 'https://data.alpaca.markets/v1'
    quote_url = market_url + '/last_quote/stocks/'

    @error_logging
    def get_watchlist_symbols(self):
            
        r = requests.get(self.watchlist_url,
                        headers=self.headers,
                        timeout=5)
        
        debug_logger.debug("API called for watchlist")
        
        watchlist = json.loads(r.content)

        watchlist_symbols = [asset['symbol'] for asset in watchlist['assets']]
        
        return watchlist_symbols
    
    
    @error_logging
    def get_positions(self):

        r = requests.get(self.positions_url,
                        headers=self.headers,
                        timeout=5)
        
        debug_logger.debug("API called for positions")
        
        positions = json.loads(r.content)

        positions_symbols = [position['symbol'] for position in positions]

        return positions_symbols
    

    @error_logging
    def place_order(self, symbol, side, qty, type='market', 
                    time_in_force='gtc', order_class='bracket'):

        params = {
            'symbol': symbol,
            'side': side,
            'qty': str(qty),
            'type': type,
            'time_in_force': time_in_force,
            'order_class': order_class,
            'take_profit': self.take_and_stop(symbol)[0],
            'stop_loss': self.take_and_stop(symbol)[1]
            }
        
        if self.is_tradable(symbol):
            
            try:
                r = requests.post(self.orders_url,
                                  params=params,
                                  headers=self.headers,
                                  timeout=5)
            except HTTPError:
                return False

        debug_logger.debug("""API called to place order for '{}'""".format(symbol))
        
        return True
            

    @error_logging
    def close_position(self, symbol):

        params = {
            'symbol': symbol,
            }

        r = requests.delete(positions_url,
                            params=params,
                            headers=self.headers,
                            timeout=5)

        debug_logger.debug("""API called to close position for '{}'""".format(symbol))
    

    @error_logging
    def is_tradable(self, symbol):

        
        asset_url = self.assets_url + symbol
        
        r = requests.get(asset_url,
                        headers=self.headers,
                        timeout=5)
        
        debug_logger.debug("""API called by is_tradable() for '{}'""".format(symbol))
        
        asset = json.loads(r.content)

        if (asset['status'] == 'active' and
            asset['tradable'] == True):

            return True
        
        else:
            return False


    # Calculate take-profit and stop-loss order prices based on last quote
    @error_logging
    def take_and_stop(self, symbol):


        last_quote_url = self.quote_url + symbol

        r = requests.get(last_quote_url,
                        headers=self.headers,
                        timeout=5)
        
        debug_logger.debug("""API called by take_and_stop() for '{}'""".format(symbol))

        quote = json.loads(r.content)
        bid = quote['last']['bidprice']
        ask = quote['last']['askprice']

        take_profit = {
                       'limit_price': str((bid / 100) * 130)
                       }
        
        stop_loss = {
                    'stop_price': str(round((ask / 100) * 90, 2)),
                    'limit_price': str(round((ask / 100) * 88, 2))
                    }
        
        return take_profit, stop_loss
