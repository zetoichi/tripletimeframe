import os
import unittest
import datetime as dt
import requests_mock
from unittest.mock import Mock, patch, call

import logging

import pandas as pd
import pandas_datareader.data as web
import requests

import scan_data as scan_data
from alpaca import Alpaca
from stock_data import Stock

logging.disable(logging.CRITICAL)

class TestStockData(unittest.TestCase):

    def setUp(self):

        self.mock_stock = Stock('FAKE')
        self.mock_dict = {
            'date': ['2019-11-12', '2019-11-13'],
            'open': [261.55, 261.13],
            'high': [262.79, 264.78],
            'low': [260.92, 261.07],
            'close': [261.96, 264.47],
            'adjusted close': [260.6421, 263.1395],
            'volume': [21847226, 25817593],
            'dividend amount': [0., 0.],
            'split coefficient': [1., 1.],
            }

        self.mock_dataframe = pd.DataFrame.from_dict(data=self.mock_dict)
        self.mock_dataframe.set_index('date')

    ### ------------------- DATA GETTERS TESTS ------------------- ###

    @patch('stock_data.web.DataReader')
    def test_get_trend_data(self, mock_datareader):

        mock_datareader.return_value = self.mock_dataframe
        mock_result_dataframe = self.mock_dataframe.copy()
        mock_result_dataframe['sma50'] = [float('nan'), float('nan')]

        actual_result = self.mock_stock.get_trend_data()

        pd.testing.assert_frame_equal(actual_result, mock_result_dataframe)

    
    @patch.object(Stock, 'get_stochastic')
    @patch('stock_data.TimeSeries')
    def test_get_tactical_data(self, mock_timeseries, mock_get_stochastic):

        mock_timeseries.return_value.get_intraday.return_value = (self.mock_dataframe, '')
        mock_result_dataframe = self.mock_dataframe.copy()
        mock_result_dataframe.rename(lambda s: '   ' + s, axis=1, inplace=True)
        mock_result_dataframe['fast k'] = [float('nan'), float('nan')]
        mock_result_dataframe['k'] = [float('nan'), float('nan')]
        mock_result_dataframe['d'] = [float('nan'), float('nan')]
        mock_get_stochastic.return_value = mock_result_dataframe

        actual_result = self.mock_stock.get_tactical_data()

        mock_get_stochastic.assert_called_once_with(self.mock_dataframe)
        pd.testing.assert_frame_equal(actual_result, mock_result_dataframe)
    

    @patch('stock_data.json.loads')
    #@patch('stock_data.pd.DataFrame.from_dict')
    @requests_mock.Mocker()
    def test_get_execution_data(self, mock_json_loads, mock_request):
        
        mock_bars = {
            "FAKE": [
                {
                "t": 1544129220,
                "o": 172.26,
                "h": 172.3,
                "l": 172.16,
                "c": 172.18,
                "v": 3892,
                }
            ]
            }
        url = 'https://data.alpaca.markets/v1/bars/1Min?symbols=FAKE&limit=10'
        mock_request.get(url, text='request ok')
        mock_json_loads.return_value = mock_bars

        actual_result = self.mock_stock.get_execution_data()

        self.assertIsInstance(actual_result, pd.DataFrame)
        
    ### ------------------- POTENTIAL GETTERS TESTS ------------------- ###
    
    def test_get_trend_potential(self):

        pass
 
    
    def test_get_tactical_potential(self):

        pass

 
    def test_get_execution_potential(self):

        pass

    ### ------------------- STATIC METHODS TESTS ------------------- ###

    def test_is_in_range_true_default_range(self):

        x = 95
        y = 105

        actual_result = self.mock_stock.is_in_range(x, y)

        self.assertEqual(actual_result, True)
    
    
    def test_is_in_range_false_default_range(self):

        x = 89
        y = 111

        actual_result = self.mock_stock.is_in_range(x, y)

        self.assertEqual(actual_result, False)

 
    def test_is_in_range_true_custom_range(self):

        x = 89
        y = 111
        range_percent = 20

        actual_result = self.mock_stock.is_in_range(x, y, range_percent)

        self.assertEqual(actual_result, True)

 
    def test_is_trending_up_true_default_step(self):

        array = [1, 2, 3]

        actual_result = self.mock_stock.is_trending_up(array)

        self.assertEqual(actual_result, True)

        
    def test_is_trending_up_false_default_step(self):

        array = [3, 1, 2]

        actual_result = self.mock_stock.is_trending_up(array)

        self.assertEqual(actual_result, False)

 
    def test_is_trending_up_true_custom_step(self):

        array = [1, 2, 3, 4, 5, 6, 7, 6, 9, 10]
        step = 2

        actual_result = self.mock_stock.is_trending_up(array, step)

        self.assertEqual(actual_result, True)

 
    def test_is_trending_up_false_custom_step(self):

        array = [1, 2, 3, 8, 5, 6, 7, 8, 9, 10]
        step = 2

        actual_result = self.mock_stock.is_trending_up(array, step)

        self.assertEqual(actual_result, False)

 