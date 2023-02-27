#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import var_models as varm
import datetime
import pandas as pd
import numpy as np
from lxml import html
import requests
import py_vollib.black.implied_volatility as pvol
import pdb
from IPython import display


# In[ ]:


def get_yyyymmdd(td):
    tds = str(td)[0:10]
    tds = tds.replace('-','')
    return int(tds)

def get_pc(sym):
    l = len(sym) - 15 
    return sym[l+6]

def get_implied_price(df_options,use_mid=True):
    strikes = [
        s for s in df_options.strike.unique()
        if len(df_options[df_options.strike==s])==2
    ]
    min_strike = min(strikes)
    c1 = df_options.strike==min_strike
    c2 = df_options.pc == 'C'
    df_min_strike_call = df_options[c1 & c2]
    c2 = df_options.pc == 'P'
    df_min_strike_put = df_options[c1 & c2]
    if use_mid:
        call_mid = (df_min_strike_call.bid.values[0] + df_min_strike_call.ask.values[0])/2
        put_mid = (df_min_strike_put.bid.values[0] + df_min_strike_put.ask.values[0])/2    
        underlying = call_mid + min_strike - put_mid
    else:
        call_last = df_min_strike_call.lastPrice.values[0]
        put_last = df_min_strike_put.lastPrice.values[0]
        underlying = call_last + min_strike - put_last
    return underlying

def implied_vol(row):
    opt_price = row.option
    und_price = row.underlying
    row_date = datetime.datetime(
        row.name.year,row.name.month,row.name.day)
    dte = row.expiry_date - row_date
    dte = dte.days/365
    rate = row.rate
    pc = row.pc.lower()
    strike = row.strike
    try:
        iv = pvol.implied_volatility(opt_price,und_price,strike,rate,dte,pc)
    except Exception as e:
        print(f"Exception: {row}")
        return None
    return iv

# def add_implied_vol(df_opt_and_under):
#     dfb = df_opt_and_under.copy()
#     dfb['iv'] = dfb.apply(
#         lambda r:implied_vol(r),
#         axis=1
#     )
#     return dfb
    
# def get_options_all_strikes_in_hist():
#     dfu = varm.yf.download(symbol,yopt.dte-datetime.timedelta(days),yopt.dte)
#     expiry_date = datetime.datetime(2023,3,17)
#     expiry_string = str(
#         (expiry_date.year-2000)*100*100 + expiry_date.month*100 + expiry_date.day
#     )
#     df_all_op = pd.DataFrame()
#     dte = yopt.dte
#     dtb = yopt.dte-datetime.timedelta(days)
#     pc = 'C'
#     strikes_to_fetch = dfu.atm_strike.unique()
#     for strike in strikes_to_fetch:
#         s = f'00000000{str(int(int(strike)*1000))}'[-8:]
#         sym = f'{symbol}{expiry_string}{pc}{s}'
#         dfo = varm.yf.download(sym,dtb,dte)
#         dfb = dfo.rename(columns={'Close':'option'}).merge(
#             dfu[['Close']].rename(columns={'Close':'underlying'}),on='Date')
#         dfb['strike'] = strike
#         dfb['pc'] = pc
#         dfb['expiry_date'] = expiry_date
#         dfb['rate'] = .04
#         df_all_op = pd.concat([df_all_op,dfb])    

def exp_string_to_datetime(exp_string):
    return datetime.datetime(
        int(exp_string[0:2])+2000,
        int(exp_string[2:4]),
        int(exp_string[4:6])
    )

def exp_datetime_to_exp_string(exp_dt):
    year = exp_dt.year
    month = exp_dt.month
    day = exp_dt.day
    yyyymmdd = year*100*100 + month*100 + day
    return str(yyyymmdd)[-6:]

class YahooOptions:
    def __init__(self,symbol,dte=None,days_of_hist=100,round_to=0):
        self.symbol = symbol
        self.ticker = varm.yf.Ticker(symbol)
        self.ticker_options_chain = self.ticker.option_chain(date=None)
        self.expirations = self.ticker._expirations
        self.dte = datetime.datetime.now() if dte is None else dte
        self.dtb = self.dte - datetime.timedelta(days_of_hist)
        self.df_und_hist = varm.yf.download(symbol,self.dtb,self.dte)
        self.prev_close = self.df_und_hist.iloc[-1].Close
        
    def get_options(self,exp_date_string):
        expirations = list(self.expirations.keys())
        if exp_date_string not in expirations:
            raise(ValueError(f"expiry {exp_date_string} not in {expirations} "))
        symbol = self.symbol
        ticker = self.ticker
        ticker_options_chain = ticker.option_chain(date=exp_date_string)
        df_ticker_options = pd.DataFrame()
        for df in ticker_options_chain:
            df_ticker_options = pd.concat([df_ticker_options,df])

        df_ticker_options['pc'] = df_ticker_options.contractSymbol.apply(get_pc)
        df_ticker_options['td_yyyymmdd'] = df_ticker_options.lastTradeDate.apply(get_yyyymmdd)
        return df_ticker_options
    
    

    def get_options_all_strikes_in_hist(
        self,expiry_datetime,strikes_to_get=None,pc='C',rounding=0,
        extended_strike_range_perc = 0.05
    ):
        exp_date_string = exp_datetime_to_exp_string(expiry_datetime)
        df_all_op = pd.DataFrame()
        dte = self.dte
        dtb = self.dtb
        strikes_to_fetch = strikes_to_get
        if strikes_to_fetch is None:
#             strikes_to_fetch = range(
#                 int(self.df_und_hist.Close.min()*(1-extended_strike_range_perc)),
#                 int(self.df_und_hist.Close.max()*(1+extended_strike_range_perc))
#             )
            strikes_to_fetch = sorted(
                [
                    int(v.round(rounding))
                    for v in self.df_und_hist.Close.values
                ]
            )
            
        dfu = self.df_und_hist
        for strike in strikes_to_fetch:
            s = f'00000000{str(int(int(strike)*1000))}'[-8:]
            sym = f'{self.symbol}{exp_date_string}{pc}{s}'
            dfo = varm.yf.download(sym,dtb,dte)
            dfb = dfo.rename(columns={'Close':'option'}).merge(
                dfu[['Close']].rename(columns={'Close':'underlying'}),on='Date')
            dfb['strike'] = strike
            dfb['pc'] = pc
            dfb['expiry_date'] = expiry_datetime
            dfb['rate'] = .04
            df_all_op = pd.concat([df_all_op,dfb])    
        
        df_all_op['iv'] = df_all_op.apply(implied_vol,axis=1)
        df_all_op = df_all_op.rename(
            columns = {
                c:c.lower().replace(' ','_') 
                for c in df_all_op.columns.values
            }
        )
        return df_all_op

    
    


# In[ ]:


if __name__=='__main__':
    yopt = YahooOptions('XLK')
    display.display(yopt.expirations)
    df_opt_all_hist = yopt.get_options_all_strikes_in_hist(
        datetime.datetime(2023,3,17)
    )
    display.display(df_opt_all_hist)


# In[ ]:


# !jupyter nbconvert --to script yahoo_options.ipynb

