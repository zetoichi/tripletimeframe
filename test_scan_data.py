import unittest
from unittest.mock import Mock, patch, call

import logging
from threading import Lock

import scan_data as scan_data
from alpaca import Alpaca
from stock_data import Stock

logging.disable(logging.CRITICAL)

class TestInitializeData(unittest.TestCase):

    @patch.object(Alpaca, 'get_watchlist')
    def test_initialize_data(self, mock_get_watchlist):

        a = Mock(spec=Alpaca)

        scan_data.initialize_data()

        self.assertEqual(mock_get_watchlist.call_count, 1)


class TestScanData(unittest.TestCase):
    """
    For all of the scan methods:
    - lock and unlock properly 
    - go through the while loop the right amount of times
    - call their corresponding get_potential() the right amount of times 
    - modify stocks data sets properly
        
    Specific for the execute_scan:
    - calls the place_order() method once and with the right arguments
    - modifies the stock.open status properly
    - modifies the stock.potential status properly
        
    """


    def setUp(self):

        logging.disable(logging.CRITICAL)
        self.mock_stock = Mock(autospec=Stock, symbol='FAKE')
        self.mock_stock.open = False
        self.fake_stocks = {
            'initial' : set(),
            'potential': set(),
            'standby': set(),
            'buy': set()
            }
        self.mock_lock = Mock(autospec=Lock)
        self.sleep = 1
        self.scans = 3
        
    ### ------------------- TREND SCAN TESTS ------------------- ###

    def test_trend_scan_with_potential(self):
        
        self.fake_stocks['initial'] = {self.mock_stock}
        self.mock_stock.potential = 2

        scan_data.trend_scan(self.fake_stocks,
                            self.mock_lock,
                            self.sleep,
                            self.scans)

        self.assertEqual(self.mock_lock.acquire.call_count, 3)
        self.assertEqual(self.mock_lock.release.call_count, 3)
        self.assertEqual(self.mock_stock.get_trend_potential.call_count, 1)
        self.assertEqual(self.fake_stocks['potential'], {self.mock_stock})


    def test_trend_scan_with_no_potential(self):

        self.fake_stocks['initial'] = {self.mock_stock}
        self.mock_stock.potential = 0

        scan_data.trend_scan(self.fake_stocks,
                            self.mock_lock,
                            self.sleep,
                            self.scans)

        self.assertEqual(self.mock_lock.acquire.call_count, 3)
        self.assertEqual(self.mock_lock.release.call_count, 3)
        self.assertEqual(self.mock_stock.get_trend_potential.call_count, 3)
        self.assertEqual(self.fake_stocks['potential'], set())

    ### ------------------- TACTICAL SCAN TESTS ------------------- ###

    def test_tactical_scan_with_strong_potential(self):
        
        self.fake_stocks['potential'] = {self.mock_stock}
        self.mock_stock.potential = 2

        scan_data.tactical_scan(self.fake_stocks,
                                self.mock_lock,
                                self.sleep,
                                self.scans)

        self.assertEqual(self.mock_lock.acquire.call_count, 3)
        self.assertEqual(self.mock_lock.release.call_count, 3)
        self.assertEqual(self.mock_stock.get_tactical_potential.call_count, 1)
        self.assertEqual(self.fake_stocks['buy'], {self.mock_stock})


    def test_tactical_scan_with_weak_potential(self):
        
        self.fake_stocks['potential'] = {self.mock_stock}
        self.mock_stock.potential = 1

        scan_data.tactical_scan(self.fake_stocks,
                                self.mock_lock,
                                self.sleep,
                                self.scans)

        self.assertEqual(self.mock_lock.acquire.call_count, 3)
        self.assertEqual(self.mock_lock.release.call_count, 3)
        self.assertEqual(self.mock_stock.get_tactical_potential.call_count, 1)
        self.assertEqual(self.fake_stocks['standby'], {self.mock_stock})
    
    
    def test_tactical_scan_with_no_potential(self):
        
        self.fake_stocks['potential'] = {self.mock_stock}
        self.mock_stock.potential = 0

        scan_data.tactical_scan(self.fake_stocks,
                                self.mock_lock,
                                self.sleep,
                                self.scans)

        self.assertEqual(self.mock_lock.acquire.call_count, 3)
        self.assertEqual(self.mock_lock.release.call_count, 3)
        self.assertEqual(self.mock_stock.get_tactical_potential.call_count, 3)
        self.assertEqual(self.fake_stocks['buy'], set())
        self.assertEqual(self.fake_stocks['standby'], set())

    ### ------------------- EXECUTE SCAN TESTS ------------------- ###
    
    @patch('scan_data.Alpaca.take_and_stop')
    @patch('scan_data.Alpaca', autospec=True)
    def test_execute_scan_with_potential(self, mock_alpaca,
                                        mock_take_and_stop):

        self.fake_stocks['buy'] = {self.mock_stock}
        self.mock_stock.potential = 2

        mock_alpaca.place_order.return_value = True
        mock_take_and_stop.return_value = (
                                {'limit_price': '100'},
                                {'stop_price': '90',
                                'limit_price': '88'}
                                )

        scan_data.execute_scan(self.fake_stocks,
                                self.mock_lock,
                                self.sleep,
                                self.scans)

        self.assertEqual(self.mock_lock.acquire.call_count, 3)
        self.assertEqual(self.mock_lock.release.call_count, 3)
        self.assertEqual(self.mock_stock.get_execution_potential.call_count, 1)
    
    
    def test_execute_scan_with_no_potential(self):

        self.fake_stocks['buy'] = {self.mock_stock}
        self.mock_stock.potential = 0

        scan_data.execute_scan(self.fake_stocks,
                                self.mock_lock,
                                self.sleep,
                                self.scans)

        self.assertEqual(self.mock_lock.acquire.call_count, 3)
        self.assertEqual(self.mock_lock.release.call_count, 3)
        self.assertEqual(self.mock_stock.get_execution_potential.call_count, 3)


#    @patch('scan_data.Alpaca.take_and_stop')
    
    @patch('scan_data.Alpaca', autospec=True)
    def test_execute_scan_buy(self, mock_alpaca):

        self.fake_stocks['buy'] = {self.mock_stock}
        self.mock_stock.potential = 2

        mock_alpaca.place_order.return_value = True
        mock_alpaca.take_and_stop.return_value = (
                                {'limit_price': '100'},
                                {'stop_price': '90',
                                'limit_price': '88'}
        )

        scan_data.execute_scan(self.fake_stocks,
                                self.mock_lock,
                                self.sleep,
                                self.scans)

        self.assertEqual(self.mock_stock.open, True)
        self.assertEqual(self.mock_stock.potential, 0)
        

if __name__ == '__main__':
    unittest.main()