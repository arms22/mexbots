# -*- coding: utf-8 -*-
from mexbots.strategy import Strategy
from mexbots.indicator import *
from mexbots.utils import reloadable_jsondict
from datetime import datetime, time

params = reloadable_jsondict('params/delta_neutral.json')

def mylogic(ticker, ohlcv, position, balance, strategy):

    # パラメータ更新
    prm = params.reload()[strategy.settings.symbol]
    sub_symbol = prm.sub_symbol
    sub_quanty = prm.sub_quanty
    sub_multiplier = prm.sub_multiplier

    # Order-Size Calculation
    sub_ticker = strategy.ticker_all[sub_symbol]
    sub_limit = sub_ticker.last
    sell_limit = ticker.ask
    sell_qty = int(sub_limit * sub_quanty / (sell_limit * sub_multiplier))

    # Positions
    short_size = max(-position.currentQty,0)
    sub_position = strategy.position_all[sub_symbol]
    sub_long_size = max(sub_position.currentQty,0)

    # 利益確定
    if position.unrealisedPnlPcnt >= 0.025:
        sell_qty = 0
    if sub_position.unrealisedPnlPcnt >= 0.025:
        sub_quanty = 0

    logger.info(f'{sell_qty}/{sell_limit} {sub_quanty}/{sub_limit}')

    # Main Order
    if short_size < sell_qty*0.98:
        qty = min(sell_qty-short_size, sell_qty)
        strategy.order('S','sell',qty=qty,limit=ticker.ask,post_only=True)
    else:
        strategy.cancel('S')
    if short_size > sell_qty*1.02:
        qty = short_size - sell_qty
        strategy.order('L','buy',qty=qty,limit=ticker.bid,post_only=True)
    else:
        strategy.cancel('L')

    # Sub Order
    if sub_long_size < sub_quanty:
        qty = min(sub_quanty-sub_long_size, sub_quanty)
        strategy.order('sL','buy',qty=qty,limit=sub_ticker.bid,post_only=True,symbol=sub_symbol)
    else:
        strategy.cancel('sL')
    if sub_long_size > sub_quanty:
        qty = sub_long_size - sub_quanty
        strategy.order('sS','sell',qty=qty,limit=sub_ticker.ask,post_only=True,symbol=sub_symbol)
    else:
        strategy.cancel('sS')

if __name__ == '__main__':
    import argparse
    import settings
    import logging
    import logging.config

    strategy = Strategy(mylogic)
    strategy.settings.timeframe = '5m'
    strategy.settings.interval = 60
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.risk.max_position_size = 3000

    parser = strategy.add_arguments(argparse.ArgumentParser(description='Delta Neutral'))
    args = parser.parse_args()
    logging.config.dictConfig(settings.loggingConf(params[args.symbol].logfilename))
    logger = logging.getLogger('delta_neutral_strategy')

    strategy.start(args)
