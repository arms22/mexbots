# -*- coding: utf-8 -*-
from mexbots.strategy import Strategy
from mexbots.indicator import *

def sar_strategy(ticker, ohlcv, position, balance, strategy):

    # インジケーター作成
    vsar = last(fastsar(ohlcv.high, ohlcv.low, 0.02, 0.06, 0.2))

	# ロット数計算
    qty_lot = int(balance.BTC.free * 0.02 * ticker.last)

    # 最大ポジション数設定
    strategy.risk.max_position_size = qty_lot

    # 注文（ポジションがある場合ドテン）
    if vsar > last(ohlcv.high):
        # STOP指値ささらなかったから成り行きでショート
        if position.currentQty >= 0:
            strategy.entry('S', 'sell', qty=qty_lot, limit=ticker.ask)

        vsar = int(vsar)
        strategy.entry('L', 'buy', qty=qty_lot, limit=vsar, stop=vsar)

    if vsar < last(ohlcv.low):
        # STOP指値ささらなかったから成り行きでロング
        if position.currentQty <= 0:
            strategy.entry('L', 'buy', qty=qty_lot, limit=ticker.bid)

        vsar = int(vsar)
        strategy.entry('S', 'sell', qty=qty_lot, limit=vsar, stop=vsar)


if __name__ == '__main__':
    import settings
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('sar_strategy.log'))
    logger = logging.getLogger("SARBot")

    strategy = Strategy(sar_strategy)
    strategy.settings.timeframe = '1m'
    strategy.settings.interval = 10
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.testnet.use = True
    strategy.testnet.apiKey = settings.testnet_apiKey
    strategy.testnet.secret = settings.testnet_secret
    strategy.start()
