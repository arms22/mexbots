# -*- coding: utf-8 -*-
from time import sleep
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import sys
import logging
import logging.config
import ccxt
import pandas as pd
from .utils import dotdict
import argparse
from bitmex_websocket import BitMEXWebsocket


def excahge_error(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        for retry in range(0, 30):
            try:
                return func(*args, **kwargs)
            except ccxt.DDoSProtection as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                waitsec = 5
            except ccxt.RequestTimeout as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                waitsec = 5
            except ccxt.ExchangeNotAvailable as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                waitsec = 20
            except ccxt.AuthenticationError as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                break
            except ccxt.ExchangeError as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                waitsec = 3
            sleep(waitsec)
        raise Exception('Exchange Error Retry Timedout!!!')
    return wrapper

class Strategy:
    resampleInfo = {
         '1m': { 'binSize' : '1m', 'resample': False, 'count': 200, 'delta':timedelta(minutes=1)  },
         '3m': { 'binSize' : '1m', 'resample': True,  'count': 120, 'delta':timedelta(minutes=1)  },
         '5m': { 'binSize' : '5m', 'resample': False, 'count': 200, 'delta':timedelta(minutes=5)  },
        '15m': { 'binSize' : '5m', 'resample': True,  'count': 120, 'delta':timedelta(minutes=5) },
        '30m': { 'binSize' : '5m', 'resample': True,  'count': 120, 'delta':timedelta(minutes=5) },
        '45m': { 'binSize' : '5m', 'resample': True,  'count': 120, 'delta':timedelta(minutes=5) },
         '1h': { 'binSize' : '1h', 'resample': False, 'count': 200, 'delta':timedelta(hours=1)    },
         '2h': { 'binSize' : '1h', 'resample': True,  'count': 200, 'delta':timedelta(hours=1)    },
         '4h': { 'binSize' : '1h', 'resample': True,  'count': 200, 'delta':timedelta(hours=1)    },
         '1d': { 'binSize' : '1d', 'resample': False, 'count': 200, 'delta':timedelta(days=1)     },
    }

    def __init__(self, yourlogic, interval=60):

        # トレーディングロジック設定
        self.yourlogic = yourlogic

        # 取引所情報
        self.settings = dotdict()
        self.settings.exchange = 'bitmex'
        self.settings.symbol = 'BTC/USD'
        self.settings.apiKey = ''
        self.settings.secret = ''
        self.settings.close_position_at_start_stop = False

        # 動作タイミング
        self.settings.interval = interval

        # ohlcv設定
        self.settings.timeframe = '1m'
        self.settings.partial = False

        # テストネット設定
        self.testnet = dotdict()
        self.testnet.use = False
        self.testnet.apiKey = ''
        self.testnet.secret = ''

        # リスク設定
        self.risk = dotdict()
        self.risk.max_position_size = 1000
        self.risk.max_drawdown = 5000

        # ポジション情報
        self.position = dotdict()
        self.position.currentQty = 0

        # 注文情報
        self.orders = dotdict()

        # ティッカー情報
        self.ticker = dotdict()

        # ohlcv情報
        self.ohlcv = None
        self.ohlcv_updated = False

        # WebSocket
        self.settings.use_websocket = False
        self.ws = None

        # ログ設定
        self.logger = logging.getLogger(__name__)

    def fetch_tickers(self, symbol=None):
        symbol = symbol or self.settings.symbol
        res = self.exchange.fetch_tickers()
        tickers = {k:dotdict(v) for k,v in res.items()}
        primary = tickers[symbol]
        self.logger.info("{symbol}: bid {bid} ask {ask} last {last}".format(**primary))
        return primary, tickers

    def fetch_ticker_ws(self):
        trade = self.ws.recent_trades()[-1]
        ticker = dotdict(self.ws.get_ticker())
        ticker.datetime = pd.to_datetime(trade['timestamp'],utc=True)
        self.logger.info("TICK: bid {bid} ask {ask} last {last}".format(**ticker))
        return ticker

    def fetch_ohlcv(self, symbol=None, timeframe=None):
        """過去100件のOHLCVを取得"""
        symbol = symbol or self.settings.symbol
        timeframe = timeframe or self.settings.timeframe
        partial = 'true' if self.settings.partial else 'false'
        rsinf = self.resampleInfo[timeframe]
        market = self.exchange.market(symbol)
        req = {
            'symbol': market['id'],
            'binSize': rsinf['binSize'],
            'count': rsinf['count'],
            'partial': partial,     # True == include yet-incomplete current bins
            'reverse': 'false',
            'startTime': datetime.utcnow() - (rsinf['delta'] * rsinf['count']),
        }
        res = self.exchange.publicGetTradeBucketed(req)
        df = pd.DataFrame(res)
        df['timestamp'] = pd.to_datetime(df['timestamp'],utc=True)
        df.set_index('timestamp', inplace=True)
        if rsinf['resample']:
            rule = timeframe
            rule = rule.replace('m','T')
            rule = rule.replace('d','D')
            df = df.resample(rule=rule, closed='right').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        self.logger.info("{symbol}: O {open} H {high} L {low} C {close} V {volume}".format(**df.iloc[-1]))
        return df

    def fetch_positions(self, symbol=None):
        """現在のポジションを取得"""
        symbol = symbol or self.settings.symbol
        res = self.exchange.privateGetPosition()
        empty = dotdict()
        empty.currentQty = 0
        empty.avgCostPrice = 0
        empty.unrealisedPnl = 0
        empty.unrealisedPnlPcnt = 0
        empty.realisedPnl = 0
        empty.symbol = symbol
        positions = defaultdict(lambda:empty)
        for p in res:
            sym = self.exchange.find_symbol(p['symbol'])
            p['symbol'] = sym
            positions[sym] = dotdict(p)
        primary = positions[symbol]
        self.logger.info("{symbol}: qty {currentQty} cost {avgCostPrice} pnl {unrealisedPnl} {realisedPnl}".format(**primary))
        return primary, positions

    def fetch_position_ws(self):
        pos = dotdict(self.ws.position())
        self.logger.info("POSITION: qty {currentQty} cost {avgCostPrice} pnl {unrealisedPnl} {realisedPnl}".format(**pos))
        return pos

    def fetch_balance(self):
        """資産情報取得"""
        balance = dotdict(self.exchange.fetch_balance())
        balance.BTC = dotdict(balance.BTC)
        self.logger.info("BALANCE: free {free:.3f} used {used:.3f} total {total:.3f}".format(**balance.BTC))
        return balance

    def fetch_balance_ws(self):
        balance = dotdict(self.ws.funds())
        balance.BTC = dotdict()
        balance.BTC.free = balance.availableMargin * 0.00000001
        balance.BTC.total = balance.marginBalance * 0.00000001
        balance.BTC.used = balance.BTC.total - balance.BTC.free
        self.logger.info("BALANCE: free {free:.3f} used {used:.3f} total {total:.3f}".format(**balance.BTC))
        return balance

    def fetch_order(self, order_id):
        order = dotdict({'status':'closed', 'id':order_id})
        try:
            order = dotdict(self.exchange.fetch_order(order_id))
            order.info = dotdict(order.info)
        except ccxt.OrderNotFound as e:
            self.logger.warning(type(e).__name__ + ": {0}".format(e))
        return order

    def fetch_order_ws(self, order_id):
        orders = self.ws.all_orders()
        for o in orders:
            if o['orderID'] == order_id:
                order = dotdict(self.exchange.parse_order(o))
                order.info = dotdict(order.info)
                return order
        return dotdict({'status':'closed', 'id':order_id})

    @excahge_error
    def close_position(self, symbol=None):
        """現在のポジションを閉じる"""
        symbol = symbol or self.settings.symbol
        market = self.exchange.market(symbol)
        req = {'symbol': market['id']}
        res = self.exchange.privatePostOrderClosePosition(req)
        self.logger.info("CLOSE: {orderID} {side} {orderQty} {price}".format(**res))

    def cancel(self, myid):
        """注文をキャンセル"""
        if myid in self.orders:
            try:
                order_id = self.orders[myid].id
                res = self.exchange.cancel_order(order_id)
                self.logger.info("CANCEL: {orderID} {side} {orderQty} {price}".format(**res['info']))
            except ccxt.OrderNotFound as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
            except ccxt.NotFound as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
            del self.orders[myid]

    @excahge_error
    def cancel_order_all(self, symbol=None):
        """現在の注文をキャンセル"""
        symbol = symbol or self.settings.symbol
        market = self.exchange.market(symbol)
        req = {'symbol': market['id']}
        res = self.exchange.privateDeleteOrderAll(req)
        for r in res:
            self.logger.info("CANCEL: {orderID} {side} {orderQty} {price}".format(**r))

    def create_order(self, side, qty, limit, stop, trailing_offset, post_only, symbol):
        type = 'market'
        params = {}
        if stop is not None and limit is not None:
            type = 'stopLimit'
            params['stopPx'] = stop
            params['execInst'] = 'LastPrice'
            params['price'] = limit
        elif stop is not None:
            type = 'stop'
            params['stopPx'] = stop
            params['execInst'] = 'LastPrice'
        elif limit is not None:
            type = 'limit'
            params['price'] = limit
            if post_only:
                params['execInst'] = 'ParticipateDoNotInitiate'
        if trailing_offset is not None:
            params['pegPriceType'] = 'TrailingStopPeg'
            params['pegOffsetValue'] = trailing_offset
        res = self.exchange.create_order(symbol, type, side, qty, None, params)
        self.logger.info("ORDER: {orderID} {side} {orderQty} {price}({stopPx})".format(**res['info']))
        return dotdict(res)

    def edit_order(self, id, side, qty, limit, stop, trailing_offset, symbol):
        type = 'market'
        params = {}
        if stop is not None and limit is not None:
            type = 'stopLimit'
            params['stopPx'] = stop
            params['price'] = limit
        elif stop is not None:
            type = 'stop'
            params['stopPx'] = stop
        elif limit is not None:
            type = 'limit'
            params['price'] = limit
        if trailing_offset is not None:
            params['pegOffsetValue'] = trailing_offset
        res = self.exchange.edit_order(id, symbol, type, side, qty, None, params)
        self.logger.info("EDIT: {orderID} {side} {orderQty} {price}({stopPx})".format(**res['info']))
        return dotdict(res)

    def order(self, myid, side, qty, limit=None, stop=None, trailing_offset=None, post_only=False, symbol=None):
        """注文"""

        qty_total = qty
        qty_limit = self.risk.max_position_size

        # 買いポジあり
        if self.position.currentQty > 0:
            # 買い増し
            if side == 'buy':
                # 現在のポジ数を加算
                qty_total = qty_total + self.position.currentQty
            else:
                # 反対売買の場合、ドテンできるように上限を引き上げる
                qty_limit = qty_limit + self.position.currentQty

        # 売りポジあり
        if self.position.currentQty < 0:
            # 売りまし
            if side == 'sell':
                # 現在のポジ数を加算
                qty_total = qty_total + -self.position.currentQty
            else:
                # 反対売買の場合、ドテンできるように上限を引き上げる
                qty_limit = qty_limit + -self.position.currentQty

        # 購入数をポジション最大サイズに抑える
        if qty_total > qty_limit:
            qty = qty - (qty_total - qty_limit)

        if qty > 0:
            symbol = symbol or self.settings.symbol

            if myid in self.orders:
                order_id = self.orders[myid].id
                order = self.fetch_order(order_id)

                # 未約定・部分約定の場合、注文を編集
                if order.status == 'open':
                    # オーダータイプが異なる or STOP注文がトリガーされたら編集に失敗するのでキャンセルしてから新規注文する
                    order_type = 'stop' if stop is not None else ''
                    order_type = order_type + 'limit' if limit is not None else order_type
                    if (order_type != order.type) or (order.type == 'stoplimit' and order.info.triggered == 'StopOrderTriggered'):
                        # 注文キャンセルに失敗した場合、ポジション取得からやり直す
                        self.exchange.cancel_order(order_id)
                        order = self.create_order(side, qty, limit, stop, trailing_offset, post_only, symbol)
                    else:
                        # 指値・ストップ価格・数量に変更がある場合のみ編集を行う
                        if ((order.info.price is not None and order.info.price != limit) or
                            (order.info.stopPx is not None and order.info.stopPx != stop) or
                            (order.info.orderQty is not None and order.info.orderQty != qty)):
                            order = self.edit_order(order_id, side, qty, limit, stop, trailing_offset, symbol)

                # 約定済みの場合、新規注文
                else:
                    order = self.create_order(side, qty, limit, stop, trailing_offset, post_only, symbol)

            # 注文がない場合、新規注文
            else:
                order = self.create_order(side, qty, limit, stop, trailing_offset, post_only, symbol)

            self.orders[myid] = order

    def entry(self, myid, side, qty, limit=None, stop=None, trailing_offset=None, symbol=None):
        """注文"""

        # 買いポジションがある場合、清算する
        if side=='sell' and self.position.currentQty > 0:
            qty = qty + self.position.currentQty

        # 売りポジションがある場合、清算する
        if side=='buy' and self.position.currentQty < 0:
            qty = qty - self.position.currentQty

        # 注文
        self.order(myid, side, qty, limit, stop, symbol)

    def update_ohlcv(self, ticker_time=None, force_update=False):
        if self.settings.partial or force_update:
            self.ohlcv = self.fetch_ohlcv()
            self.ohlcv_updated = True
        else:
            # 次に足取得する時間
            timestamp = self.ohlcv.index
            t0 = timestamp[-1]
            t1 = timestamp[-2]
            next_fetch_time = t0 + (t0 - t1)
            # 足取得
            if ticker_time > next_fetch_time:
                self.ohlcv = self.fetch_ohlcv()
                # 更新確認
                timestamp = self.ohlcv.index
                if timestamp[-1] >= next_fetch_time:
                    self.ohlcv_updated = True

    def reconnect_websocket(self):
        # 再接続が必要がチェック
        need_reconnect = False
        if self.ws is None:
            need_reconnect = True
        else:
            if self.ws.connected == False:
                self.ws.exit()
                need_reconnect = True

        # 再接続
        if need_reconnect:
            market = self.exchange.market(self.settings.symbol)
            # ストリーミング設定
            if self.testnet.use:
                self.ws = BitMEXWebsocket(endpoint='wss://testnet.bitmex.com/realtime', symbol=market['id'],
                    api_key=self.testnet.apiKey, api_secret=self.testnet.secret)
            else:
                self.ws = BitMEXWebsocket(endpoint='wss://www.bitmex.com', symbol=market['id'],
                    api_key=self.settings.apiKey, api_secret=self.settings.secret)
            # ネットワーク負荷の高いトピックの配信を停止
            self.ws.unsubscribe(['orderBookL2'])

    def setup(self):
        # 取引所セットアップ
        if self.testnet.use:
            self.exchange = getattr(ccxt, self.settings.exchange)({
                'apiKey': self.testnet.apiKey,
                'secret': self.testnet.secret,
                })
            self.exchange.urls['api'] = self.exchange.urls['test']
        else:
            self.exchange = getattr(ccxt, self.settings.exchange)({
                'apiKey': self.settings.apiKey,
                'secret': self.settings.secret,
                })
        self.exchange.load_markets()

        # マーケット一覧表示
        for k, v in self.exchange.markets.items():
            self.logger.info('Markets: ' + v['symbol'])

        # マーケット情報表示
        market = self.exchange.market(self.settings.symbol)
        self.logger.info('{symbol}: base:{base}'.format(**market))
        self.logger.info('{symbol}: quote:{quote}'.format(**market))
        self.logger.info('{symbol}: active:{active}'.format(**market))
        self.logger.info('{symbol}: taker:{taker}'.format(**market))
        self.logger.info('{symbol}: maker:{maker}'.format(**market))
        self.logger.info('{symbol}: type:{type}'.format(**market))

    def add_arguments(self, parser):
        parser.add_argument('--apikey', type=str, default=self.settings.apiKey)
        parser.add_argument('--secret', type=str, default=self.settings.secret)
        parser.add_argument('--symbol', type=str, default=self.settings.symbol)
        parser.add_argument('--timeframe', type=str, default=self.settings.timeframe)
        parser.add_argument('--interval', type=float, default=self.settings.interval)
        return parser

    def start(self, args=None):

        if args is not None:
            self.settings.apiKey = args.apikey
            self.settings.secret = args.secret
            self.settings.symbol = args.symbol
            self.settings.timeframe = args.timeframe
            self.settings.interval = args.interval

        self.logger.info("Setup Strategy")
        self.setup()

        # 全注文キャンセル
        self.cancel_order_all()

        # ポジションクローズ
        if self.settings.close_position_at_start_stop:
            self.close_position()

        self.logger.info("Start Trading")

        # 強制足取得
        self.update_ohlcv(force_update=True)

        errorWait = 0
        while True:
            self.interval = self.settings.interval

            try:
                # 例外発生時の待ち
                if errorWait:
                    sleep(errorWait)
                    errorWait = 0

                if self.settings.use_websocket:
                    # WebSocketの接続が切れていたら再接続
                    self.reconnect_websocket()

                    # ティッカー取得
                    self.ticker = self.fetch_ticker_ws()

                    # ポジション取得
                    self.position = self.fetch_position_ws()

                    # 資金情報取得
                    self.balance = self.fetch_balance_ws()
                else:
                    # ティッカー取得
                    self.ticker, self.ticker_all = self.fetch_tickers()

                    # ポジション取得
                    self.position, self.position_all = self.fetch_positions()

                    # 資金情報取得
                    self.balance = self.fetch_balance()

                # 足取得（足確定後取得）
                self.update_ohlcv(ticker_time=datetime.now(timezone.utc))

                # メインロジックコール
                arg = {
                    'strategy': self,
                    'ticker': self.ticker,
                    'ohlcv': self.ohlcv,
                    'position': self.position,
                    'balance': self.balance,
                }
                self.yourlogic(**arg)

                # 通常待ち
                sleep(self.interval)

            except ccxt.DDoSProtection as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                errorWait = 30
            except ccxt.RequestTimeout as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                errorWait = 5
            except ccxt.ExchangeNotAvailable as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                errorWait = 20
            except ccxt.AuthenticationError as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                break
            except ccxt.ExchangeError as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                errorWait = 5
            except (KeyboardInterrupt, SystemExit):
                self.logger.info('Shutdown!')
                break
            except Exception as e:
                self.logger.exception(e)
                errorWait = 5

        self.logger.info("Stop Trading")

        # 全注文キャンセル
        self.cancel_order_all()

        # ポジションクローズ
        if self.settings.close_position_at_start_stop:
            self.close_position()
