# -*- coding: utf-8 -*-
from mexbots.strategy import Strategy
from mexbots.indicator import *
from mexbots.utils import reloadable_jsondict

params = reloadable_jsondict('params/macd_cross_params.json')

def macd_cross_strategy(ticker, ohlcv, position, balance, strategy):

    # パラメータ更新チェック
    prm = params.reload()[strategy.settings.symbol]
    if params.reloaded:
        logger.info('PARAM reloaded {fastlen} {slowlen} {siglen} {percent}'.format(**prm))
        params.reloaded = False

    # インジケーター作成
    vmacd, vsig, vhist = macd(ohlcv.close, prm.fastlen, prm.slowlen, prm.siglen, use_sma=True)

    # エントリー／イグジット
    long_entry = last(crossover(vmacd, vsig))
    short_entry = last(crossunder(vmacd, vsig))

    side = 'buy' if long_entry else 'sell' if short_entry else 'none'
    logger.info('MACD {0} Signal {1} Trigger {2}'.format(last(vmacd), last(vsig), side))

    # ロット数計算
    quote = strategy.exchange.market(strategy.settings.symbol)['quote']
    if quote == 'BTC':
        qty_lot = int(balance.BTC.total * prm.percent / ticker.last)
    else:
        qty_lot = int(balance.BTC.total * prm.percent * ticker.last)
    logger.info('LOT: ' + str(qty_lot))

    # 最大ポジション数設定
    strategy.risk.max_position_size = qty_lot

    # 注文（ポジションがある場合ドテン）
    if long_entry:
        strategy.entry('L', 'buy', qty=qty_lot, limit=ticker.bid)
    else:
        strategy.cancel('L')

    if short_entry:
        strategy.entry('S', 'sell', qty=qty_lot, limit=ticker.ask)
    else:
        strategy.cancel('S')

    # ATRによるドテンロング
    if prm.use_atr_stop:
        sma_trends = last(sma(ohlcv.close, 120))
        c = last(ohlcv.close)
        logger.info('SMA Trends Close:{0}  MA:{1}'.format(c, sma_trends))
        if c > sma_trends:
            range = last(atr(ohlcv.close, ohlcv.high, ohlcv.low, 5)) * 1.6
            stop_price = int(last(ohlcv.high) + range)
            logger.info('ATR Range {0} Stop {1}'.format(range, stop_price))
        else:
            stop_price = 0
        if stop_price > 0 and position.currentQty < 0 and not long_entry and not short_entry:
            strategy.entry('doten L', side='buy', qty=qty_lot, stop=stop_price)
        else:
            strategy.cancel('doten L')

if __name__ == '__main__':
    import argparse
    import settings
    import logging
    import logging.config

    strategy = Strategy(macd_cross_strategy)
    strategy.settings.timeframe = '1h'
    strategy.settings.interval = 60
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.testnet.use = True
    strategy.testnet.apiKey = settings.testnet_apiKey
    strategy.testnet.secret = settings.testnet_secret

    parser = strategy.add_arguments(argparse.ArgumentParser(description='MACD Cross Bot'))
    args = parser.parse_args()

    logging.config.dictConfig(settings.loggingConf(params[args.symbol].logfilename))
    logger = logging.getLogger('MACDCrossBot')

    strategy.start(args)
