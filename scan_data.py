import threading
from datetime import datetime
from datetime import time 
from time import sleep

import logging
from ttf_logger import debug_logger, stock_logger

import alpaca
import record_handler as record
from stock_data import Stock
from yahoo_parser import yahoo_watchlist


class ScanThread(threading.Thread):

    def __init__(self, target, name, args, lock):

        threading.Thread.__init__(self)
        self.name = name
        self.target = target
        self.args = args
        self.lock = lock

    def run(self):
        self.lock.acquire()
        self.lock.release()
        self.target(*self.args)


today = datetime.now().strftime('%Y-%m-%d')

def initialize_data():
    """    
    Create a dict of:
        
        - initial set of Stock objects from:
            - Manually created Alpaca watchlist            
            - Automatic selection of stocks from Yahoo Finance watchlists        
        
        - 3 empty sets to be populated by stocks that:
            - show strong potential after trend scan
            - show weak potential after tactical scan
            - show strong potential after tactical scan, are ready to buy
        
        - a set of dictionaries containing information on open positions
        
        - a list of completed trades to be saved and later analized
    """
    global today

    trades = {}
    trades[today] = set()

    watchlist = alpaca.get_watchlist_symbols()
    watchlist.update(yahoo_watchlist())

    stock_logger.info("Initialized watchlist with '{}' symbols".format(len(watchlist)))

    stocks = {
        'initial': {Stock(symbol) for symbol in watchlist},
        'potential': set(),
        'standby': set(),
        'buy': set(),
        'bought': record.get_open_positions(),
        'trades': trades
        }

    debug_logger.debug("Created stocks dictionary")

    return stocks


def trend_scan(stocks, lock, sleep_time=1800):
    """
    Scan the trend data timeframe for potential, then populate the 
    potential stocks set and discard the stock if it shows no potential
    """

    while market_open():

        lock.acquire()
        debug_logger.debug("Lock acquired by trend_scan")

        for stock in stocks['initial']:

            if not stock.open:

                stock.get_trend_potential()

                debug_logger.debug("get_trend_potential for '{}'".format(stock.symbol))

                if stock.potential == 2:
                    stocks['potential'].add(stock)

                sleep(0.2)     
            
        lock.release()
        debug_logger.debug("Lock released by trend_scan")

        stock_logger.info("{} stocks have potential after trend scan".format(len(stocks['potential'])))

        sleep(sleep_time)


def tactical_scan(stocks, lock, sleep_time=600):
    """
    Scan the tactical timeframe data of each stock for potential,
    discard the stock if it shows no potential, then populate the
    standby set or buy set
    """

    while market_open():

        lock.acquire()
        debug_logger.debug("Lock acquired by tactical_scan")

        for stock in stocks['potential']: 
        
            if not stock.open:
                
                stock.get_tactical_potential()

                debug_logger.debug("get_tactical_potential for '{}'".format(stock.symbol))

                if stock.potential == 2:
                    stocks['buy'].add(stock)

                elif stock.potential == 1:   
                    stocks['standby'].add(stock)

            sleep(1)
            
        lock.release()
        debug_logger.debug("Lock released by tactical_scan")

        stock_logger.info("{} stocks have potential after tactical scan".format(len(stocks['buy'])))
        stock_logger.info("{} stocks remain in standby after tactical scan".format(len(stocks['standby'])))

        sleep(sleep_time)



def standby_scan(stocks, lock, sleep_time=120):
    """
    Re-scan the tactical timeframe for stocks that showed weak potential
    """

    while market_open():

        lock.acquire()
        debug_logger.debug("Lock acquired by standby_scan")

        for stock in stocks['standby']:
            
            if not stock.open:

                stock.get_tactical_potential()

                debug_logger.debug("get_tactical_potential for '{}'".format(stock.symbol))

                if stock.potential == 2: 
                    stocks['buy'].add(stock)

            sleep(1)
            
        lock.release()
        debug_logger.debug("Lock released by standby_scan")

        stock_logger.info("{} stocks have potential after standby".format(len(stocks['buy'])))
        
        sleep(sleep_time)
    


def execute_scan(stocks, lock, sleep_time=60):
    """
    - Scan price action to find the optimal moment for placing BUY order
    - Place order
    - Create dictionary with information on the position
    """

    while market_open():

        lock.acquire()
        debug_logger.debug("Lock acquired by execute_scan")

        for stock in stocks['buy']: 
        
            if not stock.open:

                stock.get_execution_potential()

                debug_logger.debug("get_execution_potential for '{}'".format(stock.symbol))

                if stock.potential == 2:
                    
                    alpaca.place_order(stock.symbol, 'buy', 10)    
                    stock.open_position()
                    stocks['bought'].add(stock)
                    stock_logger.info("Placed order for '{}'".format(stock.symbol))
                    
                sleep(2)
        
        lock.release()
        debug_logger.debug("Lock released by execute_scan()")
        
        stock_logger.info("Stocks of {} symbol bought".format(len(stocks['bought'])))

        sleep(sleep_time)


def sell_scan(stocks, lock, sleep_time=300):
    """
    Scans open position's unrealized profit for optimal sell signal
    """
    global today

    while market_open():
        
        lock.acquire()
        debug_logger.debug("Lock acquired by sell_scan")

        for stock in stocks['bought']:

            stock.get_sell_signal()
            debug_logger.debug("get_sell_signal for '{}'".format(stock.symbol))

            if stock.sell:

                alpaca.close_position(stock.symbol)
                stock.close_position()

                stock_logger.info("Liquidated stocks of '{}'".format(stock.symbol))
                stocks['trades'][today].add(stock.position_record)
            
            else:
                continue
                
            sleep(2)
        
        lock.release()
        debug_logger.debug("Lock released by sell_scan()")
        
        stock_logger.info("{} stocks were sold".format(len(stocks['trades'][today])))

        sleep(sleep_time)
    
    record.store_new_trades(stocks['trades'][today])


def market_open():

    market_close = time(17, 00)
    now = datetime.now()
    current_time = time(now.hour, now.minute)

    if current_time < market_close:
        return True

    return False