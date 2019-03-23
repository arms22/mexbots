# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from functools import lru_cache
from numba import jit, b1, f8, i8, void

@jit(void(f8[:],i8,i8,f8[:]),nopython=True)
def __sma_core__(v, n, p, r):
    sum = 0
    wp = 0
    q = np.empty(p)
    for i in range(p):
        r[i] = np.nan
        q[i] = v[i]
        sum = sum + q[i]
    for i in range(p,n):
        r[i-1] = sum / p
        sum = sum - q[wp]
        q[wp] = v[i]
        sum = sum + q[wp]
        wp = (wp + 1) % p
    r[n-1] = sum / p

def fastsma(source, period):
    v = source.values
    n = len(v)
    p = int(period)
    r = np.empty(n)
    __sma_core__(v,n,period,r)
    return pd.Series(r, index=source.index)

def sma(source, period):
    period = int(period)
    return source.rolling(period,min_periods=1).mean()

def dsma(source, period):
    period = int(period)
    sma = source.rolling(period).mean()
    return (sma * 2) - sma.rolling(period,min_periods=1).mean()

def tsma(source, period):
    period = int(period)
    sma = source.rolling(period).mean()
    sma2 = sma.rolling(period,min_periods=1).mean()
    return (sma * 3) - (sma2 * 3) + sma2.rolling(period,min_periods=1).mean()

def ema(source, period):
    # alpha = 2.0 / (period + 1)
    return source.ewm(span=period).mean()

def nma(source, N, period):
    alpha = N / (max(period, N) + 1)
    return source.ewm(alpha=alpha).mean()

def dema(source, period):
    ema = source.ewm(span=period).mean()
    return (ema * 2) - ema.ewm(span=period).mean()

def tema(source, period):
    ema = source.ewm(span=period).mean()
    ema2 = ema.ewm(span=period).mean()
    return (ema * 3) - (ema2 * 3) + ema2.ewm(span=period).mean()

def rma(source, period):
    alpha = 1.0 / (period)
    return source.ewm(alpha=alpha).mean()

def highest(source, period):
    period = int(period)
    return source.rolling(period,min_periods=1).max()

def lowest(source, period):
    period = int(period)
    return source.rolling(period,min_periods=1).min()

def stdev(source, period):
    period = int(period)
    return source.rolling(period,min_periods=1).std()

def variance(source, period):
    period = int(period)
    return source.rolling(period,min_periods=1).var()

def rsi(source, period):
    diff = source.diff()
    alpha = 1.0 / (period)
    positive = diff.clip_lower(0).ewm(alpha=alpha).mean()
    negative = diff.clip_upper(0).ewm(alpha=alpha).mean()
    rsi = 100-100/(1-positive/negative)
    return rsi

def stoch(close, high, low, period):
    period = int(period)
    hline = high.rolling(period).max()
    lline = low.rolling(period).min()
    return 100 * (close - lline) / (hline - lline)

def momentum(source, period):
    return source - source.shift(int(period))

def bband(source, period, mult=2.0):
    period = int(period)
    middle = source.rolling(period).mean()
    sigma = source.rolling(period).std()
    upper = middle+sigma*mult
    lower = middle-sigma*mult
    return (upper, lower, middle, sigma)

def macd(source, fastlen, slowlen, siglen, use_sma=False):
    if use_sma:
        macd = source.rolling(int(fastlen)).mean() - source.rolling(int(slowlen)).mean()
    else:
        macd = source.ewm(span=fastlen).mean() - source.ewm(span=slowlen).mean()
    signal = macd.rolling(int(siglen)).mean()
    return (macd, signal, macd-signal)

def hlband(source, period):
    period = int(period)
    high = source.rolling(period).max()
    low = source.rolling(period).min()
    return (high, low)

def wvf(close, low, period = 22, bbl = 20, mult = 2.0, lb = 50, ph = 0.85, pl=1.01):
    """
    period: LookBack Period Standard Deviation High
    bbl:    Bolinger Band Length
    mult:   Bollinger Band Standard Devaition Up
    lb:     Look Back Period Percentile High
    ph:     Highest Percentile - 0.90=90%, 0.95=95%, 0.99=99%
    pl:     Lowest Percentile - 1.10=90%, 1.05=95%, 1.01=99%
    """
    bbl = int(bbl)
    lb = int(lb)
    period = int(period)
    # VixFix
    close_max = close.rolling(period).max()
    wvf = ((close_max - low) / close_max) * 100

    sDev = mult * wvf.rolling(bbl).std()
    midLine = wvf.rolling(bbl).mean()
    lowerBand = midLine - sDev
    upperBand = midLine + sDev
    rangeHigh = wvf.rolling(lb).max() * ph
    rangeLow = wvf.rolling(lb).min() * pl
    return (wvf, lowerBand, upperBand, rangeHigh, rangeLow)

def wvf_inv(close, high, period = 22, bbl = 20, mult = 2.0, lb = 50, ph = 0.85, pl=1.01):
    """
    period: LookBack Period Standard Deviation High
    bbl:    Bolinger Band Length
    mult:   Bollinger Band Standard Devaition Up
    lb:     Look Back Period Percentile High
    ph:     Highest Percentile - 0.90=90%, 0.95=95%, 0.99=99%
    pl:     Lowest Percentile - 1.10=90%, 1.05=95%, 1.01=99%
    """
    bbl = int(bbl)
    lb = int(lb)
    period = int(period)
    # VixFix_inverse
    close_min = close.rolling(period).min()
    wvf_inv = abs(((close_min - high) / close_min) * 100)

    sDev = mult * wvf_inv.rolling(bbl).std()
    midLine = wvf_inv.rolling(bbl).mean()
    lowerBand = midLine - sDev
    upperBand = midLine + sDev
    rangeHigh = wvf_inv.rolling(lb).max() * ph
    rangeLow = wvf_inv.rolling(lb).min() * pl
    return (wvf_inv, lowerBand, upperBand, rangeHigh, rangeLow)

def tr(close, high, low):
    last = close.shift(1).fillna(method='ffill')
    tr = high - low
    diff_hc = (high - last).abs()
    diff_lc = (low - last).abs()
    tr[diff_hc > tr] = diff_hc
    tr[diff_lc > tr] = diff_lc
    return tr

def atr(close, high, low, period):
    last = close.shift(1).fillna(method='ffill')
    tr = high - low
    diff_hc = (high - last).abs()
    diff_lc = (low - last).abs()
    tr[diff_hc > tr] = diff_hc
    tr[diff_lc > tr] = diff_lc
    return tr.ewm(alpha=1.0/period).mean()

def crossover(a, b):
    cond1 = (a > b)
    return cond1 & (~cond1).shift(1)

def crossunder(a, b):
    cond1 = (a < b)
    return cond1 & (~cond1).shift(1)

def last(source, period=0):
    """
    last(close)     現在の足
    last(close, 0)  現在の足
    last(close, 1)  1つ前の足
    """
    return source.iat[-1-int(period)]

def totuple(source):
    return tuple(source.values.flatten())

def tolist(source):
    return list(source.values.flatten())

def change(source, period=1):
    return source.diff(period).fillna(0)

def falling(source, period=1):
    return source.diff(period).fillna(0)<0

def rising(source, period=1):
    return source.diff(period).fillna(0)>0

def fallingcnt(source, period=1):
    return (source.diff()<0).rolling(period, min_periods=1).sum()

def risingcnt(source, period=1):
    return (source.diff()>0).rolling(period, min_periods=1).sum()

def pivothigh(source, leftbars, rightbars):
    leftbars = int(leftbars)
    rightbars = int(rightbars)
    high = source.rolling(leftbars).max()
    diff = high.diff()
    pvhi = pd.Series(high[diff >= 0], index=source.index)
    return pvhi.shift(rightbars) if rightbars > 0 else pvhi

def pivotlow(source, leftbars, rightbars):
    leftbars = int(leftbars)
    rightbars = int(rightbars)
    low = source.rolling(leftbars).min()
    diff = low.diff()
    pvlo = pd.Series(low[diff <= 0], index=source.index)
    return pvlo.shift(rightbars) if rightbars > 0 else pvlo

@jit(void(f8[:],f8[:],i8,f8,f8,f8,f8[:]),nopython=True)
def __sar_core__(high, low, n, start, inc, max, sar):
    sar[0] = low[0]
    ep = high[0]
    acc = start
    long = True
    for i in range(1, n):
        sar[i] = sar[i-1] + acc * (ep - sar[i-1])
        if long:
            if high[i] > ep:
                ep = high[i]
                if acc < max:
                    acc += inc
            if sar[i] > low[i]:
                long = False
                acc = start
                sar[i] = ep
        else:
            if low[i] < ep:
                ep = low[i]
                if acc < max:
                    acc += inc
            if sar[i] < high[i]:
                long = True
                acc = start
                sar[i] = ep

def fastsar(high, low, start, inc, max):
    index = high.index
    high = high.values
    low = low.values
    n = len(high)
    sar = np.empty(n)
    __sar_core__(high, low, n, start, inc, max, sar)
    return pd.Series(sar, index=index)

def sar(high, low, start, inc, max):
    index = high.index
    high = high.values
    low = low.values
    n = len(high)
    sar = np.empty(n)
    sar[0] = low[0]
    ep = high[0]
    acc = start
    long = True
    for i in range(1, n):
        sar[i] = sar[i-1] + acc * (ep - sar[i-1])
        if long:
            if high[i] > ep:
                ep = high[i]
                if acc < max:
                    acc += inc
            if sar[i] > low[i]:
                long = False
                acc = start
                sar[i] = ep
        else:
            if low[i] < ep:
                ep = low[i]
                if acc < max:
                    acc += inc
            if sar[i] < high[i]:
                long = True
                acc = start
                sar[i] = ep
    return pd.Series(sar, index=index)

def minimum(a, b, period=1):
    c = a.copy()
    c[a > b] = b
    if period < 2:
        return c
    period = int(period)
    return c.rolling(period).min()

def maximum(a, b, period=1):
    c = a.copy()
    c[a < b] = b
    if period < 2:
        return c
    period = int(period)
    return c.rolling(period).max()

@lru_cache(maxsize=None)
def fib(n):
    n = int(n)
    fib = [0] * n
    fib[1] = 1
    for i in range(2, n):
        fib[i] = fib[i-2] + fib[i-1]
    return pd.Series(fib)

@lru_cache(maxsize=None)
def fibratio(n):
    n = int(n)
    f = fib(n)
    return f / f.iat[n-1]

@jit(f8(f8[:],i8,i8),nopython=True)
def __rci_d__(v, i, p):
    sum = 0.0
    for j in range(p):
        o = 1
        k = v[i-j]
        for l in range(p):
            if k < v[i-l]:
                o = o + 1
        sum = sum + (j + 1 - o) ** 2
    return sum

@jit(void(f8[:],i8,i8,f8[:]),nopython=True)
def __rci_core__(v, n, p, r):
    k = (p * (p ** 2 - 1))
    for i in range(p-1):
        r[i] = np.nan
    for i in range(p-1, n):
        r[i] = ((1.0 - (6.0 * __rci_d__(v, i, p)) / k)) * 100.0

def fastrci(source, period):
    v = source.values
    n = len(v)
    p = int(period)
    r = np.empty(n)
    __rci_core__(v,n,p,r)
    return pd.Series(r, index=source.index)

def rci(source, period):
    """
    ord(seq, idx, itv) =>
        p = seq[idx]
        o = 1
        for i = 0 to itv - 1
            if p < seq[i]
                o := o + 1
        o
    d(itv) =>
        sum = 0.0
        for i = 0 to itv - 1
            sum := sum + pow((i + 1) - ord(src, i, itv), 2)
        sum

    rci(itv) => (1.0 - 6.0 * d(itv) / (itv * (itv * itv - 1.0))) * 100.0
    """
    period = int(period)
    v = source.values
    n = len(v)
    r = np.empty(n)
    for i in range(period-1):
        r[i] = np.nan

    # rank_idx = np.array(range(1, period+1))
    # def d(isrc):
    #     rank_ord = np.argsort(v[isrc-period+1:isrc+1])
    #     return np.sum((rank_idx - rank_ord) ** 2)

    def d(isrc):
        r = 0
        ord = np.argsort(v[isrc-period+1:isrc+1])
        for i in range(period):
            r = r + (i + 1 - ord[i]) ** 2
        return r

    k = (period * (period ** 2 - 1))
    for i in range(period-1, n):
        r[i] = ((1.0 - (6.0 * d(i)) / k)) * 100.0

    return pd.Series(r, index=source.index)

def polyfline(source, period, deg=2):
    period = int(period)
    deg = int(deg)
    v = source.values
    n = len(v)
    x = np.linspace(0, period-1, period)
    poly = np.empty(n)
    for i in range(0, period):
        poly[i] = np.nan
    for i in range(period, n):
        p = np.poly1d(np.polyfit(x, v[i-period:i], deg))
        poly[i] = p(period-1)
    return pd.Series(poly, index=source.index)

def correlation(source_a, source_b, period):
    period = int(period)
    return source_a.rolling(period).corr(source_b)

def cumsum(source, period):
    return source.rolling(int(period),min_periods=1).sum()

def hlc3(ohlcv):
    return (ohlcv.high+ohlcv.low+ohlcv.close)/3

def ohlc4(ohlcv):
    return (ohlcv.open+ohlcv.high+ohlcv.low+ohlcv.close)/4

def mfi(ohlcv, period):
    tp = (ohlcv.high+ohlcv.low+ohlcv.close)/3
    mf = tp * ohlcv.volume
    df = mf.diff()
    pmf = df.clip_lower(0).rolling(period).sum()
    mmf = df.clip_upper(0).rolling(period).sum().abs()
    mr = pmf/mmf
    return 100-(100/(1+mr))

if __name__ == '__main__':

    from utils import stop_watch

    # p0 = 8000 #初期値
    # vola = 15.0 #ボラティリティ(%)
    # dn = np.random.randint(2, size=1000)*2-1
    # scale = vola/100/np.sqrt(365*24*60)
    # gwalk = np.cumprod(np.exp(scale*dn))*p0
    # data = pd.Series(gwalk)

    ohlc = pd.read_csv('csv/bitmex_2019_5m.csv', index_col='timestamp', parse_dates=True)

    fastsma = stop_watch(fastsma)
    sma = stop_watch(sma)
    dsma = stop_watch(dsma)
    tsma = stop_watch(tsma)
    ema = stop_watch(ema)
    dema = stop_watch(dema)
    tema = stop_watch(tema)
    rma = stop_watch(rma)
    rsi = stop_watch(rsi)
    stoch = stop_watch(stoch)
    wvf = stop_watch(wvf)
    highest = stop_watch(highest)
    lowest = stop_watch(lowest)
    macd = stop_watch(macd)
    tr = stop_watch(tr)
    atr = stop_watch(atr)
    pivothigh = stop_watch(pivothigh)
    pivotlow = stop_watch(pivotlow)
    sar = stop_watch(sar)
    fastsar = stop_watch(fastsar)
    minimum = stop_watch(minimum)
    maximum = stop_watch(maximum)
    rci = stop_watch(rci)
    fastrci = stop_watch(fastrci)
    polyfline = stop_watch(polyfline)
    corr = stop_watch(correlation)
    mfi = stop_watch(mfi)

    vfastsma = fastsma(ohlc.close, 10)
    vsma = sma(ohlc.close, 10)
    vdsma = dsma(ohlc.close, 10)
    vtsma = tsma(ohlc.close, 10)
    vema = ema(ohlc.close, 10)
    vdema = dema(ohlc.close, 10)
    vtema = tema(ohlc.close, 10)
    vrma = rma(ohlc.close, 10)
    vrsi = rsi(ohlc.close, 14)
    vstoch = stoch(vrsi, vrsi, vrsi, 14)
    (vwvf, lowerBand, upperBand, rangeHigh, rangeLow) = wvf(ohlc.close, ohlc.low)
    vhighest = highest(ohlc.high, 14)
    vlowest = lowest(ohlc.low, 14)
    (vmacd, vsig, vhist) = macd(ohlc.close, 9, 26, 5)
    vtr = tr(ohlc.close, ohlc.high, ohlc.low)
    vatr = atr(ohlc.close, ohlc.high, ohlc.low, 14)
    vpivoth = pivothigh(ohlc.high, 4, 2).ffill()
    vpivotl = pivotlow(ohlc.low, 4, 2).ffill()
    vsar = sar(ohlc.high, ohlc.low, 0.02, 0.02, 0.2)
    vfastsar = fastsar(ohlc.high, ohlc.low, 0.02, 0.02, 0.2)
    vmin = minimum(ohlc.open, ohlc.close, 14)
    vmax = maximum(ohlc.open, ohlc.close, 14)
    vrci = rci(ohlc.open, 14)
    vfastrci = fastrci(ohlc.open, 14)
    vply = polyfline(ohlc.open, 14)
    vcorr = corr(ohlc.close, ohlc.volume, 14)
    vmfi = mfi(ohlc, 14)
    df = pd.DataFrame({
        'high':ohlc.high,
        'low':ohlc.low,
        'close':ohlc.close,
        'fastsma':vfastsma,
        'sma':vsma,
        'dsma':vdsma,
        'tsma':vtsma,
        'ema':vema,
        'dema':vdema,
        'tema':vtema,
        'rma':vrma,
        'rsi':vrsi,
        'stochrsi':vstoch,
        'wvf':vwvf,
        'wvf-upper':upperBand,
        'wvf-lower':lowerBand,
        'wvf-high':rangeHigh,
        'wvf-low':rangeLow,
        'highest':vhighest,
        'lowest':vlowest,
        'macd':vmacd,
        'macd-signal':vsig,
        'tr':vtr,
        'atr':vatr,
        'pivot high':vpivoth,
        'pivot low':vpivotl,
        'sar':vsar,
        'fastsar':vfastsar,
        'min':vmin,
        'max':vmax,
        'rci':vrci,
        'fastrci':vfastrci,
        'polyfit':vply,
        'corr':vcorr,
        'mfi':vmfi,
        }, index=ohlc.index)
    print(df.to_csv())
