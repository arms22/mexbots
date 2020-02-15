# -*- coding: utf-8 -*-
from mexbots.strategy import Strategy
from mexbots.indicator import *
from datetime import datetime, time

interest_base = '.ETHBON8H'
interest_quote = '.USDBON'
premium = '.ETHUSDPI'
spot_symbol = '.BETHXBT'

entry_time = {
    (time( 3,45), time( 3,59)),
    (time(11,45), time(11,59)),
    (time(19,45), time(19,59)),
}

sell_entry_fr = 0.025
sell_exit_fr = 0.025
buy_entry_fr = -0.025
buy_exit_fr = -0.025

def can_entry(time_table):
    t = datetime.utcnow().time()
    result = False
    for s, e in time_table:
        if t >= s and t <= e:
            result = True
            break
    return result

def mylogic(ticker, ohlcv, position, balance, strategy):
    # Funding Calculation
    # IB = strategy.fetch_ohlcv(symbol=interest_base)
    # B = IB.close.values[-1]
    B = 0.0003

    # IQ = strategy.fetch_ohlcv(symbol=interest_quote)
    # Q = IQ.close.values[-1]
    Q = 0.0006

    pRaw = strategy.fetch_ohlcv(symbol=premium)
    p8 = sma(pRaw.close,96)
    P = p8.values[-1]
    T = 3.0
    I = (Q-B)/T
    F = P + min(max(I-P,-0.0005),0.0005)
    P_pct = P*100
    F_pct = F*100

    P8 = p8.values[-96]
    F8 = P8 + min(max(I-P8,-0.0005),0.0005)
    P8_pct = P8*100
    F8_pct = F8*100

    # Order-Size Calculation
    spot_ticker = strategy.ticker_all[spot_symbol]
    spot_limit = spot_ticker.last
    # spot_qty = 1
    spot_qty = 0.05 / spot_limit
    sell_qty = int(spot_limit * spot_qty / (ticker.ask * 0.000001))
    buy_qty = int(spot_limit * spot_qty / (ticker.bid * 0.000001))
    long_size = max(position.currentQty,0)
    short_size = max(-position.currentQty,0)

    logger.info(f'{F_pct:.4f}/{P_pct:.4f} {F8_pct:.4f}/{P8_pct:.4f} {sell_qty} {buy_qty} {spot_limit:.4f}')

    # Entry
    if can_entry(entry_time):
        if F8_pct >= sell_entry_fr and short_size < sell_qty:
            qty = min(sell_qty-short_size, sell_qty)
            strategy.order('S','sell',qty=qty,limit=ticker.ask,post_only=True)
        else:
            strategy.cancel('S')
        if F8_pct <= buy_entry_fr and long_size < buy_qty:
            qty = min(buy_qty - long_size, buy_qty)
            strategy.order('L','buy',qty=qty,limit=ticker.bid,post_only=True)
        else:
            strategy.cancel('L')
    # Exit
    else:
        strategy.cancel('S')
        strategy.cancel('L')
        if F_pct <= sell_exit_fr and short_size > 0:
            qty = short_size
            strategy.order('SC','buy',qty=qty,limit=ticker.bid,post_only=True)
        else:
            strategy.cancel('SC')
        if F_pct >= buy_exit_fr and long_size > 0:
            qty = long_size
            strategy.order('LC','sell',qty=qty,limit=ticker.ask,post_only=True)
        else:
            strategy.cancel('LC')

if __name__ == '__main__':
    import settings
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('ethusd_fr_strategy.log'))
    logger = logging.getLogger('ETHUSD_FR')

    strategy = Strategy(mylogic)
    strategy.settings.symbol = 'ETH/USD'
    strategy.settings.timeframe = '5m'
    strategy.settings.interval = 60
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.risk.max_position_size = 1000
    strategy.start()
