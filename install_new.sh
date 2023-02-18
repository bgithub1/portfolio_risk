# Create a FastAPI/Express.js project 
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# IMPORTANT: ONLY RUN THIS .sh SCRIPT USING:
# . install_new.sh myproject_name
# !!!!!!!!!! DO NOT USE:
# bash install_new.sh myproject_name
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# In this example, the project name is ivskew.  
# When you run install_new.sh, the script will create a base project of:

#ivskew/
#├── LICENSE
#├── README.md
#├── requirements.txt
#├── ivskew_server.py
#├── df_cash_futures_CB.csv
#├── df_cash_futures_CL.csv
#├── df_cash_futures_ES.csv
#├── df_cash_futures_NG.csv
#├── df_iv_final_CB.csv
#├── df_iv_final_CL.csv
#├── df_iv_final_ES.csv
#├── df_iv_final_NG.csv
#├── df_iv_skew_CB.csv
#├── df_iv_skew_CL.csv
#├── df_iv_skew_ES.csv
#├── df_iv_skew_NG.csv
#├── javascript_server/
#├──── node_modules/
#├──── public/
#├────── css/
#├──────── proj_styles.css
#├────── js/
#├──────── proj_javascript.js
#├──── express_server.js
#├──── index.html
#├──── package.jspon
#├── temp_folder/
#├──── .gitignore


# pname is the name of the new project
pname=${1}
if [[ -z ${pname} ]]
then
	pname="new_project"
fi
# bname is the full path of the base project
bname=${2}
if [[ -z ${bname} ]]
then
	bname="fastapi_express_base_project"
fi

# base_dir is the FULL path which will contain ${pname} project
base_dir=${3}
if [[ -z ${base_dir} ]]
then
	base_dir=$(cd .;pwd)
fi

# virtualenv_folder is the FULL path folder of the Virtualenv environment for your python code
virtualenv_folder=${4}
if [[ -z ${virtualenv_folder} ]]
then
	virtualenv_folder=$(cd ~/Virtualenvs3/risktables;pwd)
fi

source ${virtualenv_folder}/bin/activate
echo "Installing ${pname} in directory ${base_dir}/${pname}"
cd ${base_dir}

mkdir ${pname}
cd ${pname}
# copy top level files (like .gitignore)
cp ${base_dir}/${bname}/* .
# make the ${pname} sub directory
mkdir ${pname}
cd ${pname}
cp -r ${base_dir}/${bname}/${bname}/* .
cd javascript_server
nvm install 16.13.1
npm install express
npm install axios

