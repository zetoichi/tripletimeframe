from time import sleep

import requests
from bs4 import BeautifulSoup


def get_yahoo_watchlist_urls(section_url):
    """
    Gets the urls for all of the watchlists from one of Yahoo Finance's
    sections.
    """
    section_r = requests.get(section_url).text
    section_soup = BeautifulSoup(section_r, 'lxml')
    section_watchlists = section_soup.tbody.contents

    all_url_list = [row.find('a')['href'] for row in section_watchlists]
    no_crypto_urls = [url for url in all_url_list if 'crypto' not in url]

    return no_crypto_urls


def get_all_yahoo_watchlist_symbols(url_list):
    """
    From a list of watchlist urls, retrieves symbols for potential stocks,
    according to basic criteria
    """
    watchlist_symbols = []
    stocks_viewed = 0

    for url in url_list:
        
        print(url)
        watchlist_url = yahoo_home_url + url
        watchlist_r = requests.get(watchlist_url).text
        watchlist_soup = BeautifulSoup(watchlist_r, 'lxml')
        watchlist_table = watchlist_soup.find(class_='cwl-symbols').tbody.contents

        for row in watchlist_table:
            stocks_viewed += 1
            filter_stocks(watchlist_symbols, row)

        sleep(0.2)

    print('stocks_viewed:', stocks_viewed)
    return watchlist_symbols
                

def filter_stocks(symbol_list, row):
    """
    RULES OUT:
    - stocks already in list
    - penny stocks
    - stocks with negative change
    
    Also, double checks for Crypto symbols (separated by '-')
    """
    
    stock = {}

    stock['symbol'] = row.find('a')['title']


    if (stock['symbol'] not in symbol_list and
        '-' not in stock['symbol']):
        
        try:
            stock['price'] = float(row.find(class_='data-col2').text)
            stock['change'] = float(row.find(class_='data-col3').span.text)
        except (ValueError, AttributeError):
            pass
        else:
            if (stock['price'] > 20 and
                stock['change'] > 0):
                
                symbol_list.append(stock['symbol'])

    return symbol_list


def yahoo_watchlist():

    yahoo_home_url = 'https://finance.yahoo.com'
    top_gainers_url = yahoo_home_url + '/watchlists/category/section-gainers'

                    
    url_list = get_yahoo_watchlist_urls(top_gainers_url)
    symbol_list = get_all_yahoo_watchlist_symbols(url_list)

    return symbol_list