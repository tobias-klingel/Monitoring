import datetime
import time

from pymongo import MongoClient
from miio import AirPurifier, DeviceException

while True:
    try:
        #Connect to MongoDB
        client = MongoClient("mongodb://<username>:<pw>@XXX.XXX.XXX.XXX:27017/admin") #<--------------------To config
        db = client['{}'.format('sensors')]
        write = db['{}'.format('xiaomi_AirPurifier')]

        #Conenct to AirPurifier, (IP, token)
        xm_airP=  AirPurifier("192.168.0.XXX", "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

        #############################
        #Status data
        try:
            while True:
                #Get data
                status = xm_airP.status()

                #Creat JSON object for DB
                writeData = ({
                      'aqi': int(status.aqi),
                      'humidity': int(status.humidity),
                      'illuminance': int(status.illuminance),
                      'os_on': "{}".format(status.is_on),
                      'motor_speed': int(status.motor_speed),
                      'temp': float(status.temperature),
                      'filter_hours_used': int(status.filter_hours_used),
                      'filter_life_remaining': int(status.filter_life_remaining),
                       'average_aqi': int(status.average_aqi),
                       'mode': "{}".format(status.mode),
                       '_id': "{}".format(datetime.datetime.utcnow())})

                #Print sensor data obj
                print (writeData)

                #Write to MongoDB
                print(write.insert_one(writeData))

                print ("########################\n")
                time.sleep(60*5) #Wait 5 minutes until reuqesting next sensor data

        except Exception as e:
            print ("\nException in 'while True'(inner) Msg: ",e)
            time.sleep(10)
        #############################
    except Exception as e:
        print ("\nException in 'while True'(outer) Msg: ",e)
        time.sleep(10)
