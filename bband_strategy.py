# -*- coding: utf-8 -*-
from mexbots.strategy import Strategy
from mexbots.indicator import *

length = 20
multi = 2

def bband_strategy(ticker, ohlcv, position, balance, strategy):

    # インジケーター作成
    source = ohlcv.close
    basis = sma(source, length)
    dev = multi * stdev(source, length)
    upper = basis + dev
    lower = basis - dev

    # エントリー・エグジット
    buyEntry = crossover(source, lower)
    sellEntry = crossunder(source, upper)
    logger.info('Lower ' + str(last(lower)) + ' Upper ' + str(last(upper)))

    # ロット数計算
    qty_lot = int(balance.BTC.free * 0.01 * ticker.last)

    # 最大ポジション数設定
    strategy.risk.max_position_size = qty_lot

    # 注文（ポジションがある場合ドテン）
    if last(buyEntry):
      strategy.entry('L', 'buy', qty=qty_lot, limit=ticker.bid)
    else:
      strategy.cancel('L')
    if last(sellEntry):
      strategy.entry('S', 'sell', qty=qty_lot, limit=ticker.ask)
    else:
      strategy.cancel('S')

if __name__ == "__main__":
    import settings
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('bband_strategy.log'))
    logger = logging.getLogger("bband_strategy")

    strategy = Strategy(bband_strategy)
    strategy.settings.timeframe = '15m'
    strategy.settings.interval = 30
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.testnet.use = True
    strategy.testnet.apiKey = settings.testnet_apiKey
    strategy.testnet.secret = settings.testnet_secret
    strategy.start()
