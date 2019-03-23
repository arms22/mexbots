# -*- coding: utf-8 -*-
from mexbots.strategy import Strategy
from mexbots.indicator import *

# ロット制御パラメータ
baselot = 200
klot = 238

# ブレイクアウトエントリー期間
breakout_in = 22
breakout_out = 5

def channel_breakout_strategy(ticker, ohlcv, position, balance, strategy):

    # エントリー/エグジット
    long_entry_price = last(highest(ohlcv.high, breakout_in)) + 0.5
    short_entry_price = last(lowest(ohlcv.low, breakout_in)) - 0.5
    long_exit_price = last(lowest(ohlcv.low, breakout_out)) - 0.5
    short_exit_price = last(highest(ohlcv.high, breakout_out)) + 0.5

    # ロット数計算
    fastsma = last(sma(ohlcv.close, 13))
    slowsma = last(sma(ohlcv.close, 26))
    lots = (1 - abs(fastsma / slowsma))
    lots = (1 - lots * klot)
    lots = max(min(lots, 1.0), 0.1)
    qty_lot = int(lots * baselot)
    logger.info("LOT: " + str(qty_lot))

    # 最大ポジション数設定
    strategy.risk.max_position_size = qty_lot

    # 注文
    if position.currentQty > 0:
        if long_exit_price <= short_entry_price:
            qty = position.currentQty + qty_lot
        else:
            qty = position.currentQty
        strategy.order('L_exit', side='sell', qty=qty, limit=min(long_exit_price, ticker.ask), stop=long_exit_price)
        strategy.cancel('S')
        strategy.ohlcv_updated = False
    elif position.currentQty < 0:
        if short_exit_price >= long_entry_price:
            qty = -position.currentQty + qty_lot
        else:
            qty = -position.currentQty
        strategy.order('S_exit', side='buy', qty=qty, limit=max(short_exit_price, ticker.bid), stop=short_exit_price)
        strategy.cancel('L')
        strategy.ohlcv_updated = False
    else:
        if strategy.ohlcv_updated:
            strategy.order('L', 'buy', qty=qty_lot, limit=max(long_entry_price, ticker.bid), stop=long_entry_price)
            strategy.order('S', 'sell', qty=qty_lot, limit=min(short_entry_price, ticker.ask), stop=short_entry_price)
        else:
            logger.info("Waiting for OHLCV update...")


if __name__ == '__main__':
    import argparse
    import settings
    import logging
    import logging.config

    strategy = Strategy(channel_breakout_strategy)
    strategy.settings.timeframe = '5m'
    strategy.settings.interval = 10
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.testnet.use = True
    strategy.testnet.apiKey = settings.testnet_apiKey
    strategy.testnet.secret = settings.testnet_secret

    parser = strategy.add_arguments(argparse.ArgumentParser(description='Channel Breakout Bot'))
    parser.add_argument('--parameter', nargs=3, type=int, default=[breakout_in, breakout_out])
    args = parser.parse_args()

    logging.config.dictConfig(
        settings.loggingConf('chbrk-bot-' + args.symbol.replace('/','_').lower() + '.log'))
    logger = logging.getLogger('ChbrkBot')

    breakout_in = args.parameter[0]
    breakout_out = args.parameter[1]

    strategy.start(args)
