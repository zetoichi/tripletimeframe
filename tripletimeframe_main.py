import schedule
import time
from threading import Lock

import scan_data as scan
from alpaca import Alpaca
from stock_data import Stock
from scan_data import ScanThread


def main():
    
    loop_lock = Lock()
    thread_lock = Lock()
    data = scan.initialize_data()

    trend = ScanThread(scan.trend_scan,
                        'Trend',
                        (data, loop_lock, 900), thread_lock)

    tactical = ScanThread(scan.tactical_scan,
                        'Tactical',
                        (data, loop_lock, 300), thread_lock)
    
    execute = ScanThread(scan.execute_scan,
                        'Execute',
                        (data, loop_lock), thread_lock)
    
    standby = ScanThread(scan.standby_scan,
                        'Standby',
                        (data, loop_lock), thread_lock)

    sell = ScanThread(scan.sell_scan,
                        'Sell',
                        (data, loop_lock), thread_lock)
                        
    trend.start()
    tactical.start()
    standby.start()
    execute.start()
    sell.start()
    
    trend.join()
    tactical.join()
    standby.join()
    execute.join()
    sell.join()



schedule.every().monday.at("11:27").do(main)
schedule.every().tuesday.at("11:27").do(main)
schedule.every().wednesday.at("11:27").do(main)
schedule.every().thursday.at("11:27").do(main)
schedule.every().friday.at("11:27").do(main)

DEBUG = True

if __name__ == "__main__":
    
    if DEBUG:
        main()
    else:
        while True:
            schedule.run_pending()
            time.sleep(1)
