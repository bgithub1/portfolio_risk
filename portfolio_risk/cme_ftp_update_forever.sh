days_to_subtract=${1}
for i in {1..999999};do bash cme_ftp_update.sh $days_to_subtract;echo sleeping for a day;sleep 20000;done
