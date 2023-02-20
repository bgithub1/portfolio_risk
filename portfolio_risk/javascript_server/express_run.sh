express_port=${1}
fastapi_port=${2}
default_csv=${3}
if [[ -z ${express_port} ]]
then
	express_port=3010
fi
if [[ -z ${fastapi_port} ]]
then
	fastapi_port=8555
fi

node express_server.js ${express_port} ${fastapi_port} ${default_csv}
