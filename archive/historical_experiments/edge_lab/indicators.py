"""QCP Edge Lab vectorized causal primitives (pandas/numpy, no lookahead)."""
from __future__ import annotations
import numpy as np
import pandas as pd

def ema(close, span):
    return pd.Series(close).ewm(span=span, adjust=False).mean().to_numpy()

def atr(high, low, close, length=14):
    h=pd.Series(high); l=pd.Series(low); c=pd.Series(close); pc=c.shift(1)
    tr=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    out=np.array(tr.ewm(alpha=1.0/length, adjust=False).mean().to_numpy(),dtype=float)
    out[:length]=out[length] if len(out)>length else out[0]
    return out

def rsi(close, period=14):
    c=pd.Series(close); d=c.diff(); g=d.clip(lower=0); lo=(-d).clip(lower=0)
    ag=g.ewm(alpha=1.0/period, adjust=False).mean()
    al=lo.ewm(alpha=1.0/period, adjust=False).mean()
    rs=ag/al.replace(0,np.nan)
    out=np.array((100-100/(1+rs)).to_numpy(),dtype=float); out[:period]=50.0
    return np.nan_to_num(out,nan=50.0)

def donchian(high, low, length):
    h=pd.Series(high); l=pd.Series(low)
    return h.rolling(length).max().shift(1).to_numpy(), l.rolling(length).min().shift(1).to_numpy()

def supertrend_dir(high, low, close, atr_len=10, factor=3.0):
    import numpy as _np
    a=atr(high,low,close,atr_len); hl2=(high+low)/2; ub=hl2+factor*a; lb=hl2-factor*a
    n=len(close); fub=_np.empty(n); flb=_np.empty(n); d=_np.ones(n,dtype=int); st=_np.empty(n)
    fub[0]=ub[0]; flb[0]=lb[0]; st[0]=flb[0]
    for i in range(1,n):
        fub[i]=ub[i] if (ub[i]<fub[i-1] or close[i-1]>fub[i-1]) else fub[i-1]
        flb[i]=lb[i] if (lb[i]>flb[i-1] or close[i-1]<flb[i-1]) else flb[i-1]
        if st[i-1]==fub[i-1]:
            d[i],st[i]=(-1,fub[i]) if close[i]<=fub[i] else (1,flb[i])
        else:
            d[i],st[i]=(1,flb[i]) if close[i]>=flb[i] else (-1,fub[i])
    return d
