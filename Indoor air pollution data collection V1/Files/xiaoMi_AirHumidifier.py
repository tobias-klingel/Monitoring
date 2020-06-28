from miio import AirHumidifierCA1, DeviceException
import datetime
import time
from pymongo import MongoClient

try:
    while True:
        #Config sensor (IP, token)
        xmAH = AirHumidifierCA1('192.168.0.XXX', 'XXXXXXXXXXXXXXXXXXXXXXX')#<--------------------To config
        #Config MongoDB
        client = MongoClient("mongodb://<username>:<pw>@XXX.XXX.XXX.XXX:27017/admin") #<--------------------To config
        
        db = client['{}'.format('sensors')]  # exchangeName+'_test')]
        write = db['{}'.format('xiaomi_AirHumidifier')]

        while True:
            try:
                #Gettting data from device
                status=xmAH.status()

                #Create JSON object for DB
                writeData = ({
                    'power': "{}".format(status.power),
                    'mode': "{}".format(status.mode),
                    'temperature': float(status.temperature),
                    'humidity': int(status.humidity),
                    'motor_speed': int(status.motor_speed),
                    'use_time': int(status.use_time),
                    '_id': "{}".format(datetime.datetime.utcnow())})

                # Print sensor data obj
                print(writeData)

                # Write to MongoDB
                print(write.insert_one(writeData))

            except Exception as e:
                print('\nError in getting Humidifier data: ',e)
            time.sleep(60*5) #Wait 5 minutes until reuqesting next sensor data

except Exception as e:
    print('\nError in collection Air Humidifier data (outer loop): ', e)
