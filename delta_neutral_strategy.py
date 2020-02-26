# -*- coding: utf-8 -*-
from mexbots.strategy import Strategy
from mexbots.indicator import *
from mexbots.utils import reloadable_jsondict
from datetime import datetime, time
from math import fsum

delta_neutral_params = reloadable_jsondict('params/delta_neutral.json')

def sub_logic(main_symbol, sub_symbol, sub_quanty, sub_multiplier, strategy):

    # Order-Size Calculation
    main_ticker = strategy.ticker_all[main_symbol]
    sub_ticker = strategy.ticker_all[sub_symbol]
    sub_limit = sub_ticker.last
    sell_limit = main_ticker.ask
    sell_qty = int(sub_limit * sub_quanty / (sell_limit * sub_multiplier))

    # Positions
    main_position = strategy.position_all[main_symbol]
    sub_position = strategy.position_all[sub_symbol]
    short_size = max(-main_position.currentQty,0)
    sub_long_size = max(sub_position.currentQty,0)

    # # Take Profit
    # if main_position.unrealisedPnlPcnt >= 0.025:
    #     sell_qty = 0
    # if sub_position.unrealisedPnlPcnt >= 0.025:
    #     sub_quanty = 0

    logger.info('{symbol}: qty {currentQty} cost {avgCostPrice} pnl {unrealisedPnl} {unrealisedPnlPcnt}'.format(**main_position))
    logger.info('{symbol}: qty {currentQty} cost {avgCostPrice} pnl {unrealisedPnl} {unrealisedPnlPcnt}'.format(**sub_position))
    logger.info(f'{main_symbol} {sell_qty}/{sell_limit} {sub_symbol} {sub_quanty}/{sub_limit}')

    # Main Order
    if short_size < sell_qty*0.98:
        qty = min(sell_qty-short_size, sell_qty)
        strategy.order(main_symbol+'S','sell',qty=qty,limit=main_ticker.ask,post_only=True,symbol=main_symbol)
    else:
        strategy.cancel(main_symbol+'S')
    if short_size > sell_qty*1.02:
        qty = short_size - sell_qty
        strategy.order(main_symbol+'Sc','buy',qty=qty,limit=main_ticker.bid,post_only=True,symbol=main_symbol)
    else:
        strategy.cancel(main_symbol+'Sc')

    # Sub Order
    if sub_long_size < sub_quanty:
        qty = min(sub_quanty-sub_long_size, sub_quanty)
        strategy.order(sub_symbol+'L','buy',qty=qty,limit=sub_ticker.bid,post_only=True,symbol=sub_symbol)
    else:
        strategy.cancel(sub_symbol+'L')
    if sub_long_size > sub_quanty:
        qty = sub_long_size - sub_quanty
        strategy.order(sub_symbol+'Lc','sell',qty=qty,limit=sub_ticker.ask,post_only=True,symbol=sub_symbol)
    else:
        strategy.cancel(sub_symbol+'Lc')

def mylogic(ticker, ohlcv, position, balance, strategy):

    params = delta_neutral_params.reload()

    sub_positions = []
    for sym,prm in params['contracts'].items():
        sub_logic(
            sym,
            prm.sub_symbol,
            prm.sub_quanty,
            prm.sub_multiplier,
            strategy)
        sub_positions.append(strategy.position_all[prm.sub_symbol])

    # sub_total_size = fsum(p.currentQty*p.avgCostPrice for p in sub_positions)
    # logger.info(f'{sub_total_size}')

if __name__ == '__main__':
    import argparse
    import settings
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('delta_neutral_strategy.log'))
    logger = logging.getLogger('delta_neutral_strategy')

    strategy = Strategy(mylogic)
    strategy.settings.timeframe = '5m'
    strategy.settings.interval = 60
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.risk.max_position_size = 3000
    strategy.start()
