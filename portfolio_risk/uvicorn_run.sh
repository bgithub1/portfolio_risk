# Run ther fastapi_server via uvicorn.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# IMPORTANT
# DO NOT RUN AS: bash uvicorn_run.sh
#  RUN using "dot":  . uvicorn_run.sh
# Example: run with defaults
# . . uvicorn_run.sh
# Example: run with FastAPI port of 8557
# . uvicorn_run.sh 8557
# Example: run with FastAPI port of 8557 and origin port of 3013
# . uvicorn_run.sh 8557 3013
# Example: run with FastAPI port of 8557 and origin port of 3013 
#   and Virtualenv of ~/my_virtualenv
# . uvicorn_run.sh 8557 3013 ~/my_virtualenv

port=$1
if [[ -z ${port} ]]
then
	port=8555
fi
originport=$2
if [[ -z  ${originport} ]]
then
	originport=3010
fi
virtualenv_path=${3}
if [[ -z ${virtualenv_path} ]]
then
	virtualenv_path=$(cd ~/Virtualenvs3/risktables;pwd)
fi
source ${virtualenv_path}/bin/activate
# uvicorn fastapi_server:app --port 8555 --reload
python3 fastapi_server.py --port ${port} --originport ${originport} --host "127.0.0.1" --reload