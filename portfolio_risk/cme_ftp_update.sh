days_to_subtract_from_today=${1}
yyyymmdd=$(python3 yyyymmdd.py ${days_to_subtract_from_today});python3 cme_settle_upate_from_ftp.py --yyyymmdd $yyyymmdd
