import os
import fnmatch
import re
import time
from datetime import datetime, timedelta
import calendar
import gzip
import ldap
import sys
import subprocess

###################
#Nutno zmenit path_file a pattern
#
#
###################

dirPath = "/syslog/asa_connect_log"
fileList = os.listdir(dirPath)
for fileName in fileList:
	os.remove(dirPath+"/"+fileName)


path_file = '/syslog'
pattern = r"lenka.klembarova@pvk.cz.*Duration"

files = []
principalname = []
slovnik = {}
full_seznam = []

def date_to_timestamp(parse_time):
    struct_time = time.strptime(parse_time,'%Y %b  %d %H:%M:%S')
    dt_obj = datetime(*struct_time[0:6])
    timestamp = calendar.timegm(dt_obj.timetuple())
    return timestamp

def duration_to_timestamp(parse_duration_time):
    struct_time = time.strptime(parse_duration_time,'%Y %m %d %Hh:%Mm:%Ss')
    dt_obj = datetime(*struct_time[0:6])
    timestamp_duration = calendar.timegm(dt_obj.timetuple())
    return timestamp_duration

def rozparsuj(file,pattern):
    for radek in file.readlines():  #cteni logu
        if re.search(pattern,radek,re.IGNORECASE):
            mess_seznam = radek.split(',')
            count = 0
            seznam = []
            seznam_keys = ['Disconnect','Username','IP','Duration','sentBytes','receiveBytes','Reason','Connect','TimeStamp']
            while count != 1:
                #parsovani a pripojovani do listu
                parse_time = re.search('([A-Z].*[\d] \d\d:\d\d:\d\d)',mess_seznam[0])
                parse_time = "2016 "+parse_time.group(0)
                seznam.append(parse_time)
                parse_duration = re.search('(.*):(.*) (.*)', mess_seznam[4])
                parse_duration_time = "1970 1 1 "+parse_duration.group(3)
                parse_username =re.search('(.*) = (.*)',mess_seznam[1])
                seznam.append(parse_username.group(2))
                parse_IP = re.search('(.*) = (.*)',mess_seznam[2])
                seznam.append(parse_IP.group(2))
                seznam.append(parse_duration.group(2)+" "+parse_duration.group(3))
                parse_byteXMT = re.search('(.*): (.*)', mess_seznam[5])
                seznam.append(parse_byteXMT.group(2))
                parse_byteRCV = re.search('(.*): (.*)', mess_seznam[6])
                seznam.append(parse_byteRCV.group(2))
                parse_reason = re.search('(.*): (.*)', mess_seznam[7])
                #cas odpojeni minus doba pripojeni, ziskam dobu pripojeni, a kontrola jestli nebyl pripojen vice dni
                odecet = date_to_timestamp(parse_time) - duration_to_timestamp(parse_duration_time)
                if parse_duration.group(2) != "":
                    parse_day = re.search('(\d)',parse_duration.group(2))
                    odecet1 = duration_to_timestamp(parse_duration_time)+ int(parse_day.group(1))*int('86400')
                    odecet = date_to_timestamp(parse_time) - odecet1

                utcTime = datetime.utcfromtimestamp(odecet) #prevod z timestamp do human time
                seznam.append(parse_reason.group(2))
                utcTime = utcTime.strftime("%Y %b %d %H:%M:%S")
                seznam.append(str(utcTime))
                seznam.append(str(date_to_timestamp(parse_time))) #pridani TimeStamp do seznamu

                slovnik = dict(zip(seznam_keys,seznam)) #paruju slovnikovy klice se seznamem
                full_seznam.append(slovnik)
				print seznam
                count +=1
#vylistuje log soubory zacinajici na 10.90.31.201 v adresari a ulozi je to seznamu "files"
for file in os.listdir(path_file):
    if fnmatch.fnmatch(file,'10.90.31.201*'):
        files.append(file)

#Projde to seznam "files", kde jsou ulozeny nazvy log souboru a zavola to funkci na rozparsovani s timhle argumentem

for x in files:
    if x == '10.90.31.201.log':
        file = open('/syslog/'+x,'r')
        #pattern = r"@veoliavoda.cz.*Duration"
        rozparsuj(file,pattern)

    else:
        file = gzip.open('/syslog/'+x)
        print "\n"
        print "Oteviram : " + x
        time.sleep(1)
        #pattern = r"@veoliavoda.cz.*Duration"
        rozparsuj(file,pattern)
#nacte uzivatele z AD ze skupiny VPNusers

#vezme izvatele z AD a hleda ho v seznamu, kde jsou vsichni nalzeny z logu, pokud najde shodu vytvori csv s jeho jmenem a zapise do nej
pocet = 0
while len(full_seznam) != pocet:
    print full_seznam[pocet]['Username'] +","+ full_seznam[pocet]['Connect'][4:] +","+ full_seznam[pocet]['Disconnect'][4:] +","+ full_seznam[pocet]['Duration']+","+ full_seznam[pocet]['sentBytes']+","+ full_seznam[pocet]['receiveBytes']
    with open("/syslog/asa_connect_log/klembarova.csv",'a+') as files_w:
        if os.stat("/syslog/asa_connect_log/klembarova.csv").st_size == 0: #kontrola jestli je soubor prazdny nove vytvoreny, pokud ano tak zapise hlavicku
            files_w.write('Username,Connect,Disconnect,Duration,sentBytes,receiveBytes')
            files_w.write('\n')
        files_w.write(full_seznam[pocet]['Username'] +","+ full_seznam[pocet]['Connect'][4:] +","+ full_seznam[pocet]['Disconnect'][4:] +","+ full_seznam[pocet]['Duration']+","+ full_seznam[pocet]['sentBytes']+","+ full_seznam[pocet]['receiveBytes'])
        files_w.write('\n')
    pocet +=1
