import time
import threading

import logging
from ttf_logger import debug_logger, stock_logger

from alpaca import Alpaca
from stock_data import Stock


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


def initialize_data():
    """
    - Create a dict of sets:
        
        - initial set of Stock objects for data scanning 
          (from Alpaca watchlist)
        
        - three empty sets to be populated by stocks that:
            
            - show strong potential after trend scan
            - show weak potential after tactical scan
            - show strong potential tactical scan, are ready to buy
    """

    a = Alpaca()
    watchlist = a.get_watchlist()

    stocks = {
        'initial': {Stock(symbol) for symbol in watchlist},
        'potential': set(),
        'standby': set(),
        'buy': set()
        }

    debug_logger.debug("Created stocks dictionary")

    return stocks



def trend_scan(stocks, lock, sleep_time=1800, scans=3):
    """
    Scan the trend data (longer) timeframe for potential, then populate the 
    potential stocks set and discard the stock if it shows no potential
    """

    while scans > 0:
        lock.acquire()
        debug_logger.debug("Lock acquired by trend_scan()")

        for stock in stocks['initial']:

            if (not stock.open
                and stock not in stocks['potential']):

                stock.get_trend_potential()

                debug_logger.debug("get_trend_potential() called for '{}'".format(stock.symbol))

                if stock.potential == 2:
                    stocks['potential'].add(stock)

                time.sleep(15)     # Alpha-vantage API allows max 5 calls/min
            
        lock.release()
        debug_logger.debug("Lock released by trend_scan()")
        scans -= 1
        debug_logger.debug("{} trend scans remaining".format(scans))
        
        time.sleep(sleep_time)



def tactical_scan(stocks, lock, sleep_time=600, scans=12):
    """
    Scan the tactical (medium) timeframe data of each stock for potential,
    discard the stock if it shows no potential, then populate the
    standby set or buy set
    """

    while scans > 0:
        lock.acquire()
        debug_logger.debug("Lock acquired by tactical_scan()")

        if stocks['potential']:
            for stock in stocks['potential']: 
            
                if (not stock.open
                    and stock not in stocks['buy']
                    and stock not in stocks['standby']):
                    
                    stock.get_tactical_potential()

                    debug_logger.debug("get_tactical_potential() called for '{}'".format(stock.symbol))
    
                    if stock.potential == 2:
                        stocks['buy'].add(stock)
    
                    elif stock.potential == 1:   
                        stocks['standby'].add(stock)
    
                time.sleep(15)     # Alpha-vantage API allows max 5 calls/min
            
            lock.release()
            debug_logger.debug("Lock released by tactical_scan()")
            scans -= 1
            debug_logger.debug("{} tactical scans remaining".format(scans))

        else:
            lock.release()
            debug_logger.debug("Lock released by tactical_scan()")
            
        
        time.sleep(sleep_time)



def standby_scan(stocks, lock, sleep_time=120, scans=24):
    """
    
    """

    while scans > 0:
        lock.acquire()
        debug_logger.debug("Lock acquired by standby_scan()")

        if stocks['standby']:

            for stock in stocks['standby']:
                
                if (not stock.open
                    and stock not in stocks['buy']):

                    stock.get_tactical_potential()

                    debug_logger.debug("get_tactical_potential() called for '{}'".format(stock.symbol))

                    if stock.potential == 2: 
                        stocks['buy'].add(stock)

                time.sleep(15)
            
            lock.release()
            debug_logger.debug("Lock released by standby_scan()")
            scans -= 1
            debug_logger.debug("{} standby scans remaining".format(scans))

        else:
            lock.release()
            debug_logger.debug("Lock released by standby_scan()")
        
        time.sleep(sleep_time)
    


def execute_scan(stocks, lock, sleep_time=60, scans=40):
    """
    - Scan price action to find the optimal moment for placing BUY order
    - Place order
    - Change Stock status
    - Discard from set of potential stocks
    """

    while scans > 0:
        lock.acquire()
        debug_logger.debug("Lock acquired by execute_scan()")

        if stocks['buy']:

            for stock in stocks['buy']: 
            
                if not stock.open:

                    stock.get_execution_potential()

                    debug_logger.debug("get_execution_potential() called for '{}'".format(stock.symbol))

                    if stock.potential == 2:
                        
                        a = Alpaca()
                        # TO-DO! Add functionality to calculate optimal position?
                        # Temporarily, an arbitrary amount of 10 shares is established
                        if a.place_order(stock.symbol, 'buy', 10):
                        
                            stock.open = True
                            stock_logger.info("stock.open changed to True")
                            stock.potential = 0
                            stock_logger.info("stock.potential returned to 0")

                        else:
                            continue
                    
                time.sleep(10)
        
            lock.release()
            debug_logger.debug("Lock released by execute_scan()")
            scans -= 1
            debug_logger.debug("{} execute scans remaining".format(scans))
        
        else:
            lock.release()
            debug_logger.debug("Lock released by execute_scan()")

        time.sleep(sleep_time)