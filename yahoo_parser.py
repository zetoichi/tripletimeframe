from time import sleep

from ttf_logger import debug_logger

import requests
from bs4 import BeautifulSoup

yahoo_home_url = 'https://finance.yahoo.com'

def get_yahoo_watchlist_urls(section_url):
    """
    Gets the urls for all of the watchlists from one of Yahoo Finance's
    watchlist sections.
    """
    section_r = requests.get(section_url).text
    section_soup = BeautifulSoup(section_r, 'lxml')
    section_watchlists = section_soup.tbody.contents

    all_url_list = [row.find('a')['href'] for row in section_watchlists]
    no_crypto_urls = [url for url in all_url_list if 'crypto' not in url]

    return no_crypto_urls


def get_all_yahoo_watchlist_symbols(url_list):
    """
    From a list of watchlist urls, retrieve symbols for potential stocks
    according to basic criteria
    """
    global yahoo_home_url
    
    watchlist_symbols = set()
    stocks_analyzed = 0

    for url in url_list:

        debug_logger.debug("Analyzing '{}'".format(url))
        
        watchlist_url = yahoo_home_url + url
        watchlist_r = requests.get(watchlist_url).text
        watchlist_soup = BeautifulSoup(watchlist_r, 'lxml')
        watchlist_table = watchlist_soup.find(class_='cwl-symbols').tbody.contents

        for row in watchlist_table:

            filter_stocks(watchlist_symbols, row)
            stocks_analyzed += 1

        sleep(0.2)

    debug_logger.debug("A Total of {} stocks analyzed".format(stocks_analyzed))

    return watchlist_symbols
                

def filter_stocks(symbol_set, row):
    """
    RULES OUT:
    - stocks already in list
    - penny stocks
    - too expensive stocks
    - stocks with negative change
    
    Also, double checks for Crypto symbols (separated by '-')
    """
    
    stock = {}

    stock['symbol'] = row.find('a')['title']


    if '-' not in stock['symbol']:
        
        try:
            stock['price'] = float(row.find(class_='data-col2').text)
            stock['change'] = float(row.find(class_='data-col3').span.text)
        except (ValueError, AttributeError):
            pass
        else:
            if (20 < stock['price'] < 800 and
                stock['change'] > 0.5):
                
                symbol_set.add(stock['symbol'])
                debug_logger.debug("Added '{}' to watchlist".format(stock['symbol']))

    return symbol_set


def yahoo_watchlist():

    global yahoo_home_url

    top_gainers_url = yahoo_home_url + '/watchlists/category/section-gainers'

                    
    url_list = get_yahoo_watchlist_urls(top_gainers_url)
    symbol_set = get_all_yahoo_watchlist_symbols(url_list)

    debug_logger.debug("A total of {} stocks added to watchlist".format(len(symbol_set)))

    return symbol_set