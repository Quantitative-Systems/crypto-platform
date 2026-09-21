"""run_stream engine causal next-bar-open adverse-first cost-aware (fast)."""
from __future__ import annotations
from typing import List
import numpy as np
from .backtester import StreamResult
from .config import RISK_PCT, TAKER_FEE_PCT, SLIPPAGE_PCT, SPREAD_PCT

def run_stream(sigL, sigS, o, h, l, c, atr_arr, atr_mult, target_r, max_hold, risk_pct=RISK_PCT,
               fee_pct=None, slip_pct=None, spread_pct=None):
    n=len(c)
    sigL=np.asarray(sigL,dtype=bool); sigS=np.asarray(sigS,dtype=bool)
    idx=np.flatnonzero(sigL|sigS)
    # restrict to DEV-loop caller passing masked arrays; here generic
    realized=[]; e_idx=[]; x_idx=[]; reasons=[]; mfes=[]; maes=[]
    equity=10000.0
    fee = TAKER_FEE_PCT if fee_pct is None else fee_pct
    _sl = SLIPPAGE_PCT if slip_pct is None else slip_pct
    _sp = SPREAD_PCT if spread_pct is None else spread_pct
    slip = _sl + _sp / 2.0
    busy_until=-1; k=0
    m=len(idx)
    while k<m:
        i=int(idx[k])
        if i<1 or i>=n-1 or i<busy_until:
            k+=1; continue
        sig=1 if sigL[i] else -1
        entry=float(o[i+1]); sd=float(atr_mult*atr_arr[i])
        if sd<=0 or entry<=0:
            k+=1; continue
        sl=entry-sd if sig==1 else entry+sd
        tp=entry+target_r*sd if sig==1 else entry-target_r*sd
        unit_cost=entry*(slip*2+fee*2)
        size=(equity*risk_pct)/(sd+unit_cost) if sd+unit_cost>0 else 0.0
        if size<=0:
            k+=1; continue
        fill_e=entry+entry*slip if sig==1 else entry-entry*slip
        fee_e=fill_e*size*fee
        end=min(n,i+1+max_hold)
        seg_h=h[i+1:end]; seg_l=l[i+1:end]
        if len(seg_h)==0:
            k+=1; continue
        if sig==1:
            hit_sl=seg_l<=sl; hit_tp=seg_h>=tp
        else:
            hit_sl=seg_h>=sl; hit_tp=seg_l<=tp
        j_rel=None; reason=None; raw=None
        both=np.flatnonzero(hit_sl&hit_tp)
        osl=np.flatnonzero(hit_sl); otp=np.flatnonzero(hit_tp)
        if len(both): j_rel=int(both[0]); raw=sl; reason="SL"
        elif len(osl) and (not len(otp) or osl[0]<otp[0]): j_rel=int(osl[0]); raw=sl; reason="SL"
        elif len(otp): j_rel=int(otp[0]); raw=tp; reason="TP"
        else: j_rel=len(seg_h)-1; raw=float(c[i+1+j_rel]); reason="TIME"
        j=i+1+j_rel
        # MFE/MAE over holding window
        if sig==1:
            mfe_px=float(np.max(seg_h[:j_rel+1])) if j_rel>=0 else fill_e
            mae_px=float(np.min(seg_l[:j_rel+1])) if j_rel>=0 else fill_e
        else:
            mfe_px=float(np.min(seg_l[:j_rel+1])) if j_rel>=0 else fill_e
            mae_px=float(np.max(seg_h[:j_rel+1])) if j_rel>=0 else fill_e
        fill_x=raw-raw*slip if sig==1 else raw+raw*slip
        fee_x=fill_x*size*fee
        gross=(fill_x-fill_e)*size if sig==1 else (fill_e-fill_x)*size
        net=gross-fee_e-fee_x
        ref=equity*risk_pct
        r=net/ref if ref>0 else 0.0
        if sig==1: mfe=max(0.0,(mfe_px-fill_e)/sd); mae=max(0.0,(fill_e-mae_px)/sd)
        else: mfe=max(0.0,(fill_e-mfe_px)/sd); mae=max(0.0,(mae_px-fill_e)/sd)
        realized.append(r); e_idx.append(i+1); x_idx.append(j); reasons.append(reason); mfes.append(mfe); maes.append(mae)
        equity+=net; busy_until=j+1
        # advance k past busy window
        while k<m and int(idx[k])<busy_until:
            k+=1
    ra=np.array(realized) if realized else np.array([])
    if len(ra)==0:
        return StreamResult()
    w=ra[ra>0]; ls=ra[ra<0]; net=float(ra.sum()); cum=np.cumsum(ra)
    dd=float(np.max(np.maximum.accumulate(cum)-cum))
    pf=float(w.sum()/abs(ls.sum())) if len(ls) and ls.sum()!=0 else 999.0
    return StreamResult(n=len(ra),net_r=net,expectancy_r=net/len(ra),win_rate=len(w)/len(ra),profit_factor=pf,max_dd_r=dd,avg_win_r=float(w.mean()) if len(w) else 0.0,avg_loss_r=float(abs(ls.mean())) if len(ls) else 0.0,realized=ra,entry_idx=np.array(e_idx,dtype=int),exit_idx=np.array(x_idx,dtype=int),exit_reason=reasons,mfe_r=np.array(mfes),mae_r=np.array(maes))
