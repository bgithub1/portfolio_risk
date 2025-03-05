#!/usr/bin/env python
# coding: utf-8

# ## cme_settle_update_from_ftp
# Fetch cme.settle.yyyymmdd.s.csv.zip from ftp.cmegroup.com, unzip it, and then run an analysis of the 100 basis point strangle strategy

# In[4]:


import sys
import os
import datetime
import ftplib
import zipfile

import pandas as pd
import numpy as np

import yfinance as yf
from lxml import html
import requests
import py_vollib.black.implied_volatility as pvol
import pdb
from IPython import display
import plotly_utilities as pu



# In[1]:


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
        self.ticker = yf.Ticker(symbol)
        self.ticker_options_chain = self.ticker.option_chain(date=None)
        self.expirations = self.ticker._expirations
        self.dte = datetime.datetime.now() if dte is None else dte
        self.dtb = self.dte - datetime.timedelta(days_of_hist)
        self.df_und_hist = yf.download(symbol,self.dtb,self.dte)
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
            dfo = yf.download(sym,dtb,dte)
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

    def select_atm_options_only(self,df_all_op):
        '''
        @param df_all_op: The DataFrame that the method get_options_all_strikes_in_hist
                            returns
        '''
        df_all_op['afm'] = df_all_op.strike - df_all_op.underlying
        df_all_op['afm'] = df_all_op['afm'].abs()
        df_all_op_gb = df_all_op[
            ['afm']
        ].groupby(
            by=[df_all_op.index],
        ).min()
        
        df_opt_all_2 = df_all_op.merge(
            df_all_op_gb,left_index=True,right_index=True,how='left'
        )
        df_opt_all_2 =  df_opt_all_2[df_opt_all_2.afm_x==df_opt_all_2.afm_y]
        df_opt_all_2 = df_opt_all_2.drop_duplicates()
        return df_opt_all_2
        
    


# ### Below are methods that: 
# 1. get the *current* values of stock options,
# 2. show the break-even values for a simple strategy which purchases a one day ATM Strangle

# In[5]:


def get_stock_hist(sym,dte=None,dtb=None):
    if dte is None:
        dte = datetime.datetime.now()
    if dtb is None:
        dtb = datetime.datetime(2022,5,20)

    df_stock = yf.download(sym,dtb,dte)
    df_stock['pct_chg'] = df_stock.Close.pct_change()
    df_vix = yf.download('^VIX',dtb,dte)
    df_vix = df_vix.rename(columns={'Close':'VIX'})
    df_stock = df_stock.merge(df_vix[['VIX']],left_index=True,right_index=True)
    df_stock = df_stock.iloc[1:]
    return df_stock

def get_options_chain(
    underlying_symbol,
    mid_strk,
    strike_range=12,
    expiry_string=None,    
):
    if expiry_string is None:
        dt = datetime.datetime.now() + datetime.timedelta(1)
        ymd = str(dt.year*100*100+dt.month*100+dt.day)
        expiry_string = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
        
    low_strk = mid_strk - int(strike_range/2)
    high_strk = mid_strk + int(strike_range/2)
    strikes = np.arange(low_strk,high_strk+1).tolist()
    ticker = yf.Ticker(underlying_symbol)
    # ticker_options_chain = ticker.option_chain(date=None)
    ticker_options_chain = ticker.option_chain(date=expiry_string)
    dfc = ticker_options_chain[0]
    dfc2 = dfc[dfc.strike.isin(strikes)].copy()
    dfc2['mid'] = (dfc2.ask+dfc2.bid)/2

    dfp = ticker_options_chain[1]
    dfp2 = dfp[dfp.strike.isin(strikes)].copy()
    dfp2['mid'] = (dfp2.ask+dfp2.bid)/2
    return dfc2,dfp2

def strangle_strat(df_stock,dfc2,dfp2,ms):
    ps = ms - 2
    cs = ms + 2
    put = float(str(dfp2[dfp2.strike==ps].mid.values[0]))
    call = float(str(dfc2[dfc2.strike==cs].mid.values[0]))
    
    # returns is a dict of strategy parameters
    returns = {
        'strikes':[ps,cs,ms],
        'put_call':[put,call],
        'put_call_sum':put+call,
        'break_even_pct':(put+call+ms-ps)/ms,
        'strangle_premium':(put+call)/((ps+cs)/2),
        'strike_percents':[(ps-ms)/ms,(cs-ms)/ms],
        'opt_price_percents':[put/ms,call/ms]

    }

    df_stk2 = df_stock.copy()
    # pl_calc = lambda pct_chg: max(
    #     -1*returns['strangle_premium'],
    #     abs(pct_chg) - returns['break_even_pct']
    # ) 
    def pl_calc(pct_chg): 
        if abs(pct_chg)<returns['break_even_pct']:
            return -1*returns['strangle_premium']
        else:
            return abs(pct_chg) - returns['break_even_pct']


    df_stk2['pl'] = df_stk2.pct_chg.apply(pl_calc)

    df_stk2['cum_pl'] = df_stk2.pl.cumsum()
#     df_stk2[['pct_chg','pl','cum_pl']] 
    return returns,df_stk2

def plot_strat(df_stk2):
    df_stk3 = df_stk2.copy()
    df_stk3['yyyymmdd'] = [
        d.year*100*100+d.month*100+d.day
        for d in df_stk3.index.to_pydatetime()
    ]

    df_stk3['yyyymmdd'] = [
        d[0:4] + '-' + d[4:6] + '-' + d[6:8]
        for d in df_stk3.yyyymmdd.astype(str).values
    ]

    x_value_labels = [
        f"{d.year}-{('0'+str(d.month))[0:2]}-{('0'+str(d.day))[0:2]}"
        for d in df_stk3.index.to_pydatetime()
    ]

    df_stk3.index = list(range(len(df_stk3)))
    bdate = df_stk3.yyyymmdd.values[0]
    edate = df_stk3.yyyymmdd.values[-1]
    fig = pu.plotly_plot(
        df_stk3[['yyyymmdd','cum_pl']],
        'yyyymmdd',
        plot_title=f"Long Daily Strangle Strategy from {bdate} to {edate}"
    )
    return fig
    
def get_stock_list_hist(sym_list,dte=None,dtb=None):
    df_all = get_stock_hist(sym_list[0],dte=dte,dtb=dtb)
    df_all = df_all[['Close']].rename(columns={'Close':sym_list[0]}).copy()
    if len(sym_list)<2:
        return df_all
    for s in sym_list[1:]:
        df_temp = get_stock_hist(s,dte=dte,dtb=dtb)
        df_temp = df_temp[['Close']].rename(columns={'Close':s}).copy()
        df_all = df_all.merge(df_temp,how='left',left_index=True,right_index=True)
    return df_all
    


# In[6]:


def round_to_n(v,n):
    b = round(v/n,0)
    l = b*n
    h = (b+1)*n
    return l if (v - l) < (h - v) else h


# In[ ]:





# ### use csv files extracted from the CME's FTP site to show the results of the strangle strategy above, but using the *ES* contracts on the CME, rather than the options on the *SPY*

# In[7]:


if __name__=='__main__':
    """
    To run:
    python3 cme_settle_upate_from_ftp.py --yyyymmdd 20230411
    """
    yyyymmdd_of_zip = None
    for i in range(len(sys.argv)):
        if sys.argv[i]=='--yyyymmdd':
            yyyymmdd_of_zip = int(sys.argv[i+1])
            break
    if yyyymmdd_of_zip is None:
        raise ValueError('No --yyyymmdd specified')
    filename = f"cme.settle.{yyyymmdd_of_zip}.s.csv.zip"
    # Login to the FTP site
    ftp = ftplib.FTP("ftp.cmegroup.com")
    ftp.login()

    # Change directory to the desired location
    ftp.cwd("/pub/settle")

    # Download the gzip file
    dest_dir = 'temp_folder'
    full_filename = f'{dest_dir}/{filename}'
    with open(full_filename, "wb") as f:
        ftp.retrbinary("RETR " + filename, f.write)

    ftp.quit()

    # Define the input and output file names
    input_file = full_filename
    output_folder = dest_dir

    # Create a ZipFile object for the input file
    with zipfile.ZipFile(input_file, "r") as zip_ref:
        # Extract all contents of the input file to the output folder
        zip_ref.extractall(output_folder)

    # Print a message indicating the file has been unzipped
    print(f"{input_file} has been unzipped to {output_folder}.")

    yyyymmdd = yyyymmdd_of_zip
    expiry_str = None
    symbol_regex = None#'^E[12345]'
    if symbol_regex is None:
        symbol_regex = '^E[12345]'
    yyyy = str(yyyymmdd)[0:4]
    mm = str(yyyymmdd)[4:6]
    dd = str(yyyymmdd)[6:8]
    if expiry_str is None:
        expiry_str = f'{yyyy}-{mm}-{dd}'
    f = f'temp_folder/cme.settle.{yyyymmdd}.s.csv'
    df_cme = pd.read_csv(f)

    # get options
    c1 = df_cme.Sym.str.contains(symbol_regex)
    c2 = df_cme.MatDt > expiry_str
    c3 = df_cme.SecTyp=='OOF'
    c_all = c1 & c2 & c3
    df_cme_options = df_cme[c_all].copy()

    mat_dt = df_cme_options.MatDt.min()
    c2 = df_cme.MatDt==mat_dt
    c3 = df_cme.SecTyp=='OOF'
    c_all = c1 & c2 & c3
    df_cme_options = df_cme[c_all].copy()
    display.display(df_cme_options[['MatDt','Sym']].drop_duplicates().sort_values(['MatDt','Sym']))
    c1 = df_cme.Sym==df_cme_options.iloc[0]['UndlyID']
    c3 = df_cme.SecTyp==df_cme_options.iloc[0]['UndlySecTyp']
    c4 = df_cme.MMY == df_cme_options.iloc[0]['UndlyMMY']
    c_all = c1 & c3 & c4

    df_under = df_cme[c_all].copy()
    future = df_under.iloc[0].SettlePrice
    c3 = df_cme_options.SecTyp=='OOF'
    c4 = df_cme_options.PutCall==0
    c5 = df_cme_options.StrkPx <= future
    c6 = df_cme_options.StrkPx >= future*.9
    c_all = c3 & c4 & c5 & c6
    cols = ['BizDt','StrkPx','PutCall','FixingPrice','SettlePrice','MatDt']
    df_cme_puts = df_cme_options[c_all][cols]
    c3 = df_cme_options.SecTyp=='OOF'
    c4 = df_cme_options.PutCall==1
    c5 = df_cme_options.StrkPx >= future
    c6 = df_cme_options.StrkPx <= future*1.1
    c_all = c3 & c4 & c5 & c6
    df_cme_calls = df_cme_options[c_all][cols]

    display.display(df_under[cols])
    display.display(df_cme_puts[-5:])
    display.display(df_cme_calls[:5])

    # calculate break even percent
    m = round_to_n(round(future),5)
    put_price = df_cme_puts[df_cme_puts.StrkPx == (m-20)].iloc[0].SettlePrice
    call_price = df_cme_calls[df_cme_calls.StrkPx == (m+20)].iloc[0].SettlePrice
    be = (put_price + call_price + 20)/m
    display.display(f"break even percent = {be}")
                          


# In[ ]:


# !jupyter nbconvert --to script cme_settle_upate_from_ftp.ipynb

