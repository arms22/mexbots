# -*- coding: utf-8 -*-
from mexbots.strategy import Strategy
from mexbots.indicator import *

class eth_macross:

    def __init__(self):
        pass

    def loop(self, ticker, ohlcv, position, balance, strategy, **other):
        eth_ohlcv = strategy.fetch_ohlcv(symbol='ETH/USD', timeframe='5m')

        # 指標作成
        fst = sma(change(eth_ohlcv.close), 6)
        slw = sma(change(eth_ohlcv.close),60)
        co = crossover(fst,slw)[-1]
        cu = crossunder(fst,slw)[-1]

        # ロット計算
        qty_lot = int(balance.BTC.total * 4 * ticker.last)
        strategy.risk.max_position_size = qty_lot

        # エントリー
        if co:
            strategy.cancel('S exit')
            strategy.entry('L', 'buy', qty=qty_lot)
        elif cu:
            strategy.cancel('L exit')
            strategy.entry('S', 'sell', qty=qty_lot)

        # 利確指値
        if position.currentQty>0 and ohlcv.close[-1]>position.avgCostPrice+5:
            strategy.order('L exit', 'sell', qty=position.currentQty, limit=ticker.ask)
        elif position.currentQty<0 and ohlcv.close[-1]<position.avgCostPrice-5:
            strategy.order('S exit', 'buy', qty=-position.currentQty, limit=ticker.bid)


if __name__ == "__main__":
    import argparse
    import settings
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('ETHMACross.log'))
    logger = logging.getLogger('ETHMACrossBot')

    strategy = Strategy(eth_macross().loop)
    strategy.settings.timeframe = '5m'
    strategy.settings.interval = 30
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.testnet.use = True
    strategy.testnet.apiKey = settings.testnet_apiKey
    strategy.testnet.secret = settings.testnet_secret

    parser = strategy.add_arguments(argparse.ArgumentParser(description='ETH MA Cross Bot'))
    strategy.start(parser.parse_args())
