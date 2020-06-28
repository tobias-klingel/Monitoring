import datetime
import time

from btlewrap import available_backends, BluepyBackend, GatttoolBackend, PygattBackend

from miflora.miflora_poller import MiFloraPoller, \
    MI_CONDUCTIVITY, MI_MOISTURE, MI_LIGHT, MI_TEMPERATURE, MI_BATTERY

from pymongo import MongoClient

########################
mac='C4:7C:XX:XX:XX:XX' #<--------------------To config
########################

#MongoDB
client=MongoClient("mongodb://<username>:<pw>@XXX.XXX.XXX.XXX:27017/admin") #<--------------------To config
db = client['{}'.format('sensors')]  # exchangeName+'_test')]
write = db['{}'.format('xiaomi_flowerCare_'+mac)]


poller = MiFloraPoller(mac, GatttoolBackend)

##############################################################
#Functions
###########

#Flower care provides historical data
def getHistory(poller):
	history_list = poller.fetch_history()
	print('History returned {} entries.'.format(len(history_list)))
	historyData=[]
	for entry in history_list:
		print('History from {}'.format(entry.wall_time))
		historyData.append({
            '_id':entry.wall_time,
            'temperature':entry.temperature,
            'Moisture':entry.moisture,
            'light':entry.light,
            'conductivity':entry.conductivity
                })
	return historyData

#Used to get once some key data from the sensor and write it in MongoDB collection of that sensor
def initialData(poller,mac):
	initialData=({
        '_id':'InitialData',
        'timestamp':datetime.datetime.utcnow(),
        'mac':mac,
        'firmware_version':poller.firmware_version(),
        'name':poller.name(),
        'battery':poller.parameter_value(MI_BATTERY)
            })
	return initialData

#Get current battery level
def getBattery(poller):
	return poller.parameter_value(MI_BATTERY)

#Get current reading of the sensors
def getSensorData(poller):
	currentSensorData={
		'_id': datetime.datetime.utcnow(),
		'temperature': poller.parameter_value(MI_TEMPERATURE),
		'moisture': poller.parameter_value(MI_MOISTURE),
		'light': poller.parameter_value(MI_MOISTURE),
		'conductivity': poller.parameter_value(MI_CONDUCTIVITY)
            }
	return currentSensorData

##############################
#Calling functions

#Wrtie historical data to DB
def writeHistoricalDataToDB(poller):
	#Write historical data
	try:
		historyData=getHistory(poller)
		print('Number of historical data is: ',len(historyData))
		result=write.insert_many(historyData,ordered=False)
		print('\nTime now',datetime.datetime.utcnow())
		print('Result writing historical data: ', result.acknowledged)
	except Exception as e:
		# Will throw an error if historical data exist already
		print('Error writing "writeHistoricalDataToDB". Msg: ', e)

#Wrtie current data to DB
def writeCurrentSensorDataToDB(poller):
	#Write current data
	try:
		currentSensorData=getSensorData(poller)
		result=write.insert_one(currentSensorData)
		print('\nTime now',datetime.datetime.utcnow())
		print('Result writing current sensor data: ', result.acknowledged)
	except Exception as e:
		# Will throw an error if historical data exist already
		print('Error writing "writeCurrentSensorDataToDB". Msg: ', e)

##############################################################
##############################################################
#Main

#Write initial sensor data to database
try:
	initialDataObj=initialData(poller,mac)
	result=write.insert_one(initialDataObj)
	#print('\nResult writing inital data: ', result.acknowledged)
except Exception as e:
	#Will throw an error if inital entry exist already
    print('Error writing "initialData". Msg: ',e)

#Initial historical data write
print('\nWrite inital historical data to database')
writeHistoricalDataToDB(poller)

###################################
#Set start time to track daily historical data writes
startTime=time.time()
dayNum =1
writeSensorDataEverySec=60*30 #Write every 30 min

#####################
#Main loop
#####################
while True:
	time.sleep(writeSensorDataEverySec)
	poller = MiFloraPoller(mac, GatttoolBackend)
	writeCurrentSensorDataToDB(poller)
	
	#Write every day all historical data to DB
	if time.time()>=startTime+(dayNum*60*60*24):
		print('Write daily historical data')
		writeHistoricalDataToDB(poller)
		dayNum+=1
