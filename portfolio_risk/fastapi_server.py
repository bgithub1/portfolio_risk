import pandas as pd
import datetime
import pdb
from fastapi import Depends, FastAPI
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from pydantic import BaseModel

from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
import uvicorn

import pytz
from IPython import display
import argparse
import json
import var_models
import risk_tables


app = FastAPI()

YOUR_DOMAIN = 'www.yourdomain.com'

# list valid cross-origin origins
origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://www.yourdomain.com",
    "https://www.yourdomain.com",
    "http://yourdomain.com",
    "https://yourdomain.com",
    "http://localhost",
    "http://localhost:3010",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The GlobalVariables class allows you to populate global variables from the __main__
#  Below, I define a redis_port variable that I might want to use later in one of the 
#  FastAPI routes.  For now it is unused.
class GlobalVariables:
    pass
__m = GlobalVariables()  # m will contain all module-level values
__m.redis_port = None  # database name global in module
__m.origins = origins



@app.get("/")
async def root():
    return {"message": "Welcome to Risk Tables Server"}

@app.get("/get_var")
async def get_var():
    df_port = pd.read_csv('spdr_stocks.csv')
    var_model = var_models.VarModel(df_port)
    var_results = var_model.compute_var()
    return_dict = {}
    for k in var_results.keys():
        r = var_results[k]
        if type(r) == pd.DataFrame:
            r = r.to_dict(orient="records")
        return_dict[k] = r
    return return_dict


@app.get("/get_risk")
async def get_risk_tables():
    df_port = pd.read_csv('spdr_stocks.csv')
    rt = risk_tables.RiskCalcs(use_postgres=False,redis_port = __m.redis_port)
    var_results = rt.calculate(df_port)
    return_dict = {}
    for k in var_results.keys():
        r = var_results[k]
        if k[:2] == 'df':
             r = pd.DataFrame(r).to_dict(orient="records")
        return_dict[k] = r
    return return_dict

class CsvData(BaseModel):
    data: str


@app.post("/riskdata_from_csv")
async def get_risk_tables_from_csv(csv_data: CsvData):
    csv_text = csv_data.data
    if csv_text[0] == '"':
        csv_text = csv_text[1:]
    if csv_text[-1] == '"':
        csv_text = csv_text[0:-1]
    print(type(csv_text))
    print(csv_text)
    list_data = csv_text.split(';')
    list_data = [
        v.split(',')
        for v in list_data
        if len(v)>0
    ]
    dict_data = [
        {'symbol':v[0],'position':int(v[1])}
        for v in list_data[1:]
    ]
    df_port = pd.DataFrame(dict_data)
    rt = risk_tables.RiskCalcs(use_postgres=False,redis_port=__m.redis_port)
    var_results = rt.calculate(df_port)
    return_dict = {}
    for k in var_results.keys():
        r = var_results[k]
        if k[:2] == 'df':
             r = pd.DataFrame(r).to_dict(orient="records")
        return_dict[k] = r
    return return_dict


def transform_df(df:pd.DataFrame):
    # do something with DataFrame
    return df



# @app.post("/df_from_csv")
# async def df_from_csv_text(csv_text: CsvData):
#     # This route is an http post route, that accepts a text string of 
#     #   csv data.  Each csv line is separated by a ";".  The csv data on 
#     #   each line is separated by a ",".
#     # The route parses the input csv_text, and returns a json version
#     #   of a DataFrame from that text.
#     csv_text = csv_text.data
#     print(type(csv_text))
#     print(csv_text)
#     list_data = csv_text.split(';')
#     list_data = [
#         v.split(',')
#         for v in list_data
#         if len(v)>0
#     ]
#     cols = list_data[0]
#     dict_data = [
#         {cols[i]:v[i] for i in range(len(cols))}
#         for v in list_data[1:]
#         if len(v)==len(cols)
#     ]
#     df = pd.DataFrame(dict_data)
#     df = transform_df(df)
#     return_dict = df.to_dict(orient='records')
#     return {'csv_data_from_df':return_dict}

# @app.post("/df_from_csv")
# async def df_from_csv_json(csv_json_in: CsvData):
#   # This route is an http post route, that accepts a text string of 
#   #   csv data.  Each csv line is separated by a ";".  The csv data on 
#   #   each line is separated by a ",".
#   # The route parses the input csv_text, and returns a json version
#   #   of a DataFrame from that text.
#   print(type(csv_json_in))
#   print(csv_json_in)
#   csv_json_text = csv_json_in.data
#   csv_json = json.loads(csv_json_text)
#   df = pd.DataFrame(csv_json)
#   df = transform_df(df)
#   return_dict = df.to_dict(orient='records')
#   return {'csv_data_from_df':return_dict}



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            prog = 'risk_server',
            description = 'A FastAPI restAPI',
            )
    hour = datetime.datetime.now().hour
    parser.add_argument('--host',default='127.0.0.1',type=str,help="uvicorn http host") 
    parser.add_argument('--port',default=8555,type=int,help="uvicorn http port")
    parser.add_argument('--originport',default=3010,type=int,help="express origin http port")
    parser.add_argument('--reload',
        help="Tell uvicorn to automatically reload server if source code changes",
        action='store_true'
    ) 
    parser.add_argument('--log_level',default='info',type=str,
            help="the logger's log level")
    parser.add_argument('--redis_port',default=None,type=int,
        help="Redis port, if you are going to use Redis fetch data") 
    args = parser.parse_args()  
    print(args)
    __m.redis_port = args.redis_port
    __m.origins.append(f"http://localhost:{args.originport}")

    uvicorn.run(
        "fastapi_server:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload, 
        log_level=args.log_level
    )