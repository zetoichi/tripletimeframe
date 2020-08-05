import requests_mock
import unittest
from unittest.mock import Mock, patch, call

import logging

import os
import datetime as dt
import json

from alpaca import Alpaca

logging.disable(logging.CRITICAL)

class TestAlpaca(unittest.TestCase):

    _watchlist_url = 'https://paper-api.alpaca.markets/v2/watchlists/5605708b-df0a-4473-8d76-a1303e608587'
    _positions_url = 'https://paper-api.alpaca.markets/v2/positions'
    _orders_url = 'https://paper-api.alpaca.markets/v2/orders'
    _assets_url = 'https://paper-api.alpaca.markets/v2/assets/FAKE'
    _quote_url = 'https://data.alpaca.markets/v1/last_quote/stocks/FAKE'
    
    def setUp(self):

        self.alpaca = Alpaca()


    @requests_mock.Mocker()
    def test_get_watchlist(self, mock_request):

        mock_request.get(self._watchlist_url, content=b'{"watchlist_id": "fake123", "assets": [{"symbol": "FAKE"}]}')

        actual_result = self.alpaca.get_watchlist()

        self.assertEqual(actual_result, ['FAKE'])

    
    @requests_mock.Mocker()
    def test_get_positions(self, mock_request):

        mock_request.get(self._positions_url, content=b'[{"asset_id": "fake123", "symbol": "FAKE"}]')

        actual_result = self.alpaca.get_positions()

        self.assertEqual(actual_result, ['FAKE'])

    @patch('alpaca.Alpaca.take_and_stop')
    @patch('alpaca.Alpaca.is_tradable')
    @requests_mock.Mocker()
    def test_place_order(self, mock_is_tradable, mock_take_and_stop, mock_request):

        mock_request.post(self._orders_url, text='ok')
        mock_is_tradable.return_value = True
        mock_take_and_stop.return_value = (
                                {'limit_price': '130.0'},
                                {'stop_price': '90.0',
                                'limit_price': '88.0'}
                                )        
        
        actual_result = self.alpaca.place_order('FAKE', 'buy', 15)

        self.assertEqual(actual_result, True)


    @requests_mock.Mocker()
    def test_is_tradable_true(self, mock_request):

        mock_request.get(self._assets_url, content=b'{"status": "active", "tradable": true}')

        actual_result = self.alpaca.is_tradable('FAKE')

        self.assertEqual(actual_result, True)

 
    @requests_mock.Mocker()
    def test_is_tradable_false_inactive(self, mock_request):

        mock_request.get(self._assets_url, content=b'{"status": "inactive", "tradable": true}')

        actual_result = self.alpaca.is_tradable('FAKE')

        self.assertEqual(actual_result, False)

 
    @requests_mock.Mocker()
    def test_is_tradable_false_not_tradable(self, mock_request):

        mock_request.get(self._assets_url, content=b'{"status": "active", "tradable": false}')

        actual_result = self.alpaca.is_tradable('FAKE')

        self.assertEqual(actual_result, False)

 
    @requests_mock.Mocker()
    def test_take_and_stop(self, mock_request):

        mock_request.get(self._quote_url, content=b'{"symbol": "FAKE", "last": {"bidprice": 100, "askprice": 100}}')
        expected_result = (
                            {'limit_price': '130.0'},
                            {'stop_price': '90.0',
                            'limit_price': '88.0'}
                            )
        
        actual_result = self.alpaca.take_and_stop('FAKE')

        self.assertEqual(actual_result, expected_result)