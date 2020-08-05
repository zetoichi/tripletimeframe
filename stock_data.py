import os
import datetime as dt
import json

import logging
from ttf_logger import debug_logger, stock_logger, error_logging

import pandas as pd
import pandas_datareader.data as web
import requests
from alpha_vantage.timeseries import TimeSeries

#logging.disable(logging.CRITICAL)

class Stock:

    # API ACCESS (ENVIRONMENT VARIABLES)
    av_api_key = os.environ.get('ALPHAVANTAGE_API_KEY')
    alpaca_api_key = os.environ.get('ALPACA_API')
    alpaca_api_secret = os.environ.get('ALPACA_SECRET')
    
    alpaca_headers = {
        'APCA-API-KEY-ID': alpaca_api_key,
        'APCA-API-SECRET-KEY': alpaca_api_secret
        }


    def __init__(self, symbol, trend_timeframe='av-daily-adjusted',
                 tactical_timeframe='60min', execution_timeframe='1Min',
                 sma_windows=(50,), stoch_windows=(8,3,5)):
        
        """
        String representing the symbol of the stock
        """
        self.symbol = symbol
        
        """
        The 3 different timeframes that the algorithm will scan concurrently
        to find buy potential in a stock
        """
        self.trend_timeframe = str(trend_timeframe)
        self.tactical_timeframe = str(tactical_timeframe)
        self.execution_timeframe = str(execution_timeframe)
        
        """
        The time windows of moving averages that will be calculated by the
        algorithm in different stages:
        
        - Simple Moving Average
        - Stochastic k and d values
        """
        self.sma_windows = tuple(sma_windows)
        self.stoch_windows = tuple(stoch_windows)

        """
        Indicate if data for stock shows potential in each timeframe:
        
        - 0 = no potential
        - 1 = weak or unconfirmed potential
        - 2 = strong potential

        Although both the Trend and the Execution evaluations return binary
        results (buy/don't buy), the Tactical stage offers the possibility that
        the stock shows a weaker signal, giving way to further analysis before
        confirming or discarding
        """
        self.potential = 0

        """
        Indicate if the stock position is already open
        """
        self.open = False

    
    @error_logging
    def get_trend_data(self):
        """
        - Get data for the first and longest timeframe
        - Calculate Simple Moving Averages
        - Return last 60 rows
        """
        
        start = dt.datetime(2020, 1, 1) - dt.timedelta(max(self.sma_windows))
        end = dt.datetime.now()

        trend = web.DataReader(self.symbol, self.trend_timeframe,
                               start, end, api_key=self.av_api_key)

        for sma in self.sma_windows:
            trend['sma' + str(sma)] = trend['adjusted close'].rolling(sma).mean()
        
        return trend.iloc[-60:]


    @error_logging
    def get_tactical_data(self):
        """
        - Get data for the second timeframe
        - Calculate stochastic values for the given time windows
        - Return last 20 rows
        """
        
        ts = TimeSeries(self.av_api_key, output_format='pandas')
        intra = ts.get_intraday(self.symbol, self.tactical_timeframe)[0]
        
        # Rename columns and sort rows for consistency between dataframes
        intra.rename(lambda s: s[3:], axis=1, inplace=True) 
        intra.sort_index(inplace=True)

        full_intra = self.get_stochastic(intra)

        debug_logger.debug("Calculated Stochastic for '{}'".format(self.symbol))

        return full_intra.iloc[-20:]

    
    @error_logging
    def get_execution_data(self, limit=10):
        """
        - Get and return real-time price action data
        """
        
        url = ('https://data.alpaca.markets/v1/bars/' +
               self.execution_timeframe)

        params = {
            'symbols': str(self.symbol),
            'limit': int(limit)
            }
        
        rename_dict = {
            't': 'time',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            }

        r = requests.get(url, params=params, headers=self.alpaca_headers)
        execution = pd.DataFrame.from_dict(json.loads(r.content)[self.symbol])

        # Rename columns for consistency between dataframes
        execution.rename(rename_dict, axis=1, inplace=True)

        return execution


    # Calculate and store Stochastic values
    @error_logging
    def get_stochastic(self, df):

        # Unpack given Stochastic windows
        fastk, k, d = self.stoch_windows

        df['rolling high'] = df['high'].rolling(fastk).mean()
        df['rolling low'] = df['low'].rolling(fastk).mean()
        
        df['fast k'] = (
            (df['close'] - df['rolling low']) /
            (df['rolling high'] - df['rolling low'])
            ) * 100

        df['k'] = df['fast k'].rolling(k).mean()
        df['d'] = df['k'].rolling(d).mean()

        return df


    @error_logging
    def get_trend_potential(self):

        trend_data = self.get_trend_data()

        debug_logger.debug("get_trend_data() called for '{}'".format(
                            self.symbol))

        # Check if recent close prices are above the trend (SMA).
        if trend_data['adjusted close'].ge(trend_data['sma50']).all():

            last_month_smas = trend_data['sma50'].iloc[-30:].values

            # Check if market trend is bullish by comparing
            # last month SMA values between in 10 day periods.
            if self.is_trending_up(last_month_smas, step=10):
            
                last_lows = trend_data['low'].iloc[-6:].values

                stock_logger.info("'{}' is trending up".format(self.symbol))
                
                # Check if there is a recent pull-back against that trend.
                if not self.is_trending_up(last_lows):

                    last_low = trend_data['low'].iloc[-1]
                    last_sma = trend_data['sma50'].iloc[-1]
                    
                    stock_logger.info("'{}' is in a recent pull-back".format(self.symbol))
                    
                    # Check if the last low is within a small range of the sma50:
                    # It's about to meet resistance, and could be ready to resume the trend.
                    if self.is_in_range(last_low, last_sma):
                        
                        stock_logger.info("'{}' is in range".format(self.symbol))

                        self.potential = 2

        stock_logger.info("'{}' potential is now: {}".format(self.symbol,
                            self.potential))


    @error_logging
    def get_tactical_potential(self):

        self.potential = 0        # Initialize potential signal

        tactical_data = self.get_tactical_data()

        debug_logger.debug("get_tactical_data() called for '{}'".format(
                            self.symbol))

        last_k = tactical_data['k'].iloc[-1]
        last_d = tactical_data['d'].iloc[-1]

        stock_logger.info("'{}' Last K: {}".format(self.symbol, last_k))
        stock_logger.info("'{}' Last D: {}".format(self.symbol, last_d))

        if self.is_in_range(last_k, last_d):

            # Weak buy signal
            self.potential = 1

            if last_k >= last_d:
                # Strong buy signal
                self.potential = 2

        stock_logger.info("'{}' potential is now: {}".format(self.symbol,
                            self.potential))
    
    
    @error_logging
    def get_execution_potential(self):
        
        self.potential = 0        # Initialize potential signal

        execution_data = self.get_execution_data()

        debug_logger.debug("get_execution_data() called for '{}'".format(
                            self.symbol))

        last_three_highs = execution_data['high'].iloc[-3:].values

        stock_logger.info("'{}' Last 3 highs: {}".format(self.symbol, last_three_highs))

        if self.is_trending_up(last_three_highs):

            # Strong buy signal
            self.potential = 2

        stock_logger.info("'{}' potential is now: {}".format(self.symbol,
                            self.potential))
    

    @staticmethod
    def is_in_range(x, y, range_percent=10):

        bottom = (y / 100) * (100 - range_percent)
        top = (y / 100) * (100 + range_percent)

        if bottom <= x <= top or top <= x <= bottom:
            return True
        else:
            return False

    
    @staticmethod
    def is_trending_up(array, step=1):

        trending_up = False

        if step == 1:
            end = 0
        else:
            end = step

        for i in range(len(array)-1, end, -step):
            
            if array[i] >= array[i-step]:
                trending_up = True
            else:
                trending_up = False
                return trending_up
        
        return trending_up