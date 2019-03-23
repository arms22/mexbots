# -*- coding: utf-8 -*-

# APIキー設定
apiKey = ''
secret = ''

# ストラテジー設定
exchange = 'bitmex'
symbol = 'BTC/USD'
timeframe = '1h'
max_position_size = 100
interval = 60

# テストネット利用
use_testnet = True
testnet_apiKey = ''
testnet_secret = ''

# ロギング設定
def loggingConf(filename='bitbot.log'):
    return {
        'version': 1,
        'formatters':{
            'simpleFormatter':{
                'format': '%(asctime)s %(levelname)s:%(name)s:%(message)s',
                'datefmt': '%Y/%m/%d %H:%M:%S'}},
        'handlers': {
            'fileHandler': {
                'formatter':'simpleFormatter',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': 'INFO',
                'filename': filename,
                'encoding': 'utf8',
                'when': 'D',
                'interval': 1,
                'backupCount': 5},
            'consoleHandler': {
                'formatter':'simpleFormatter',
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'stream': 'ext://sys.stderr'}},
        'root': {
            'level': 'INFO',
            'handlers': ['fileHandler', 'consoleHandler']},
        'disable_existing_loggers': False
    }