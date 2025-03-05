import sys,datetime
o = 0
#print(sys.argv)
if len(sys.argv)>1:
   o = int(sys.argv[1])
d = datetime.datetime.now() - datetime.timedelta(o)
yyyymmdd = d.year*100*100 + d.month*100 + d.day
print(yyyymmdd,end="")
