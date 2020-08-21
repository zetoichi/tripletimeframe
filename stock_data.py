import os
import json
from datetime import datetime
from datetime import timedelta

import logging
from ttf_logger import debug_logger, stock_logger

import pandas as pd
import requests

import alpaca

class Stock:

    # API ACCESS (ENVIRONMENT VARIABLES)
    api_key = os.environ.get('ALPACA_API')
    api_secret = os.environ.get('ALPACA_SECRET')
    
    headers = {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': api_secret
        }


    def __init__(self, symbol, trend_timeframe='day',
                 tactical_timeframe='60Min', execution_timeframe='1Min',
                 sma_windows=(50,), stoch_windows=(8,3,5), open=False):
        
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
        self.open = open
        self.sell = False

        self.position_record = {}


    def get_data(self, timeframe, limit=1000):
        
        bars = alpaca.get_bars(self.symbol, timeframe, limit)
        data = pd.DataFrame.from_dict(bars)

        # Rename columns for clarity
        rename_dict = {
            't': 'time',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            }

        data.rename(rename_dict, axis=1, inplace=True)

        return data


    def get_open_position(self):

        position = alpaca.get_open_position(self.symbol)
        
        position['cost_basis'] = float(position['cost_basis'])
        position['unrealized_plpc'] = float(position['unrealized_plpc'])

        return position

    
    def get_trend_data(self):
        """
        - Get data for the first and longest timeframe
        - Calculate Simple Moving Averages
        - Return last 60 rows
        """

        trend = self.get_data(self.trend_timeframe, limit=200)

        for sma in self.sma_windows:
            trend['sma' + str(sma)] = trend['close'].rolling(sma).mean()
        
        return trend.iloc[-60:]


    def get_tactical_data(self):
        """
        - Get data for the second timeframe
        - Calculate stochastic values for the given time windows
        - Return last 20 rows
        """
        
        if self.tactical_timeframe == '60Min':

            data = self.get_data('15Min', limit=0)
            data_resampled = self.alpaca_data_resample(data)
            tactical =self.get_stochastic(data_resampled)
            debug_logger.debug("Calculated Stochastic for '{}'".format(self.symbol))

            return tactical.iloc[-20:]
        
        else:

            data = self.get_data(self.tactical_timeframe, limit=0)
            tactical =self.get_stochastic(data)
            debug_logger.debug("Calculated Stochastic for '{}'".format(self.symbol))

            return tactical.iloc[-20:]


    def get_execution_data(self):
        """
        - Get and return real-time price action data
        """

        return self.get_data(self.execution_timeframe)


    def alpaca_data_resample(self, data):

        data['time'] = data['time'].apply(datetime.fromtimestamp)
        data.set_index('time', inplace=True)

        params = {'rule': timedelta(hours=1),
        'offset': timedelta(minutes=30)}

        data_resample = pd.DataFrame()
        data_resample['open'] = data['open'].resample(**params).asfreq()
        data_resample['high'] =  data['high'].resample(**params).max()
        data_resample['low'] =  data['low'].resample(**params).min()
        data_resample['close'] = data['close'].shift(-3).resample(**params).asfreq()
        data_resample['volume'] = data['volume'].resample(**params).sum()
        data_resample.dropna(inplace=True)

        return data_resample

    
    def create_position_record(self):

        position = {
            'bought_on': datetime.now().strftime('%H:%M:%S'),
            'cost_basis': 0,
            'unrealized_plpc': 0,
            'max_unrealized_plpc': 0,
            'sold on': None
            }
        
        self.position_record[self.symbol] = position


    def open_position(self):

        self.create_position_record()
        self.open = True
        self.potential = 0


    def close_position(self):

        self.position_record['sold on'] = datetime.now().strftime('%H:%M:%S')
        self.open = False
        self.sell = False


    # Calculate and store Stochastic values
    def get_stochastic(self, data):

        # Unpack given Stochastic windows
        fastk, k, d = self.stoch_windows

        data['rolling high'] = data['high'].rolling(fastk).max()
        data['rolling low'] = data['low'].rolling(fastk).min()
        
        data['fast k'] = (
            (data['close'] - data['rolling low']) /
            (data['rolling high'] - data['rolling low'])
            ) * 100

        data['k'] = data['fast k'].rolling(k).mean()
        data['d'] = data['k'].rolling(d).mean()

        return data
    

    def get_trend_potential(self):

        trend_data = self.get_trend_data()

        debug_logger.debug("get_trend_data called for '{}'".format(
                            self.symbol))

        last_month_smas = trend_data['sma50'].iloc[-30:].values
        last_lows = trend_data['low'].iloc[-6:].values
        last_low = trend_data['low'].iloc[-1]
        last_sma = trend_data['sma50'].iloc[-1]
        
        if (trend_data['close'].ge(trend_data['sma50']).all() and
            self.is_trending_up(last_month_smas, step=10) and not
            self.is_trending_up(last_lows) and
            self.is_in_range(last_low, last_sma)):

            self.potential = 2
            
        stock_logger.info("'{}' potential is now: {}".format(self.symbol,
                            self.potential))


    def get_tactical_potential(self):

        self.potential = 0        # Initialize potential signal

        tactical_data = self.get_tactical_data()

        debug_logger.debug("get_tactical_data called for '{}'".format(
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
    
    
    def get_execution_potential(self):
        
        self.potential = 0        # Initialize potential signal

        execution_data = self.get_execution_data()

        debug_logger.debug("get_execution_data called for '{}'".format(
                            self.symbol))

        last_three_highs = execution_data['high'].iloc[-3:].values

        stock_logger.info("'{}' Last 3 highs: {}".format(self.symbol, last_three_highs))

        if self.is_trending_up(last_three_highs):

            # Strong buy signal
            self.potential = 2

        stock_logger.info("'{}' potential is now: {}".format(self.symbol,
                            self.potential))
    
    
    def get_sell_signal(self, trailing_pc=8):

        trailing_pc = 1 - (trailing_pc/100)

        current = self.get_open_position()
        stored = self.position_record

        if not stored['cost_basis']:
            stored['cost_basis'] = current['cost_basis']
        
        gain = current['unrealized_plpc']
        max_gain = stored['max_unrealized_plpc']
        
        stored['unrealized_plpc'] = gain

        if gain > max_gain:
            max_gain = gain

            stock_logger.info("New max_gain for '{}'".format(self.symbol))
        
        else:
            tactical_data = self.get_tactical_data()

            last_k = tactical_data['k'].iloc[-1]
            last_d = tactical_data['d'].iloc[-1]

            if (gain < (max_gain * trailing_pc) or
                last_k <= last_d):

                self.sell = True


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
