# Run ther fastapi_server via uvicorn.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# IMPORTANT
# DO NOT RUN AS: bash uvicorn_run.sh
#  RUN using "dot":  . uvicorn_run.sh
#
virtualenv_path=${1}
if [[ -z ${virtualenv_path} ]]
then
	virtualenv_path=$(cd ~/Virtualenvs3/risktables;pwd)
fi
source ${virtualenv_path}/bin/activate
# uvicorn fastapi_server:app --port 8555 --reload
python3 fastapi_server.py --port 8555 --host "127.0.0.1" --reload