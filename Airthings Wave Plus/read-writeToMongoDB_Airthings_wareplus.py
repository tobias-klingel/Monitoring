# Based on:
# https://github.com/Airthings/waveplus-reader
# https://airthings.com


# ===============================
# Module import dependencies
# ===============================

from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate
import sys
import time
import struct
import datetime
from pymongo import MongoClient

# ===============================
# Config <--------------------------------------------------------------------------------------------------------------------------------
# ===============================

#SerialNumber on the back of the device
SerialNumber = XXXXXXXXXXXX #<-------------------- Set the serial number of your device
SamplePeriod = 5*60 #Wait 5 min after each read of the data



# ====================================
# Utility functions for WavePlus class
# ====================================

def parseSerialNumber(ManuDataHexStr):
    if (ManuDataHexStr == "None"):
        SN = "Unknown"
    else:
        ManuData = bytearray.fromhex(ManuDataHexStr)

        if (((ManuData[1] << 8) | ManuData[0]) == 0x0334):
            SN  =  ManuData[2]
            SN |= (ManuData[3] << 8)
            SN |= (ManuData[4] << 16)
            SN |= (ManuData[5] << 24)
        else:
            SN = "Unknown"
    return SN

# ===============================
# Class WavePlus
# ===============================

class WavePlus():

    def __init__(self, SerialNumber):
        self.periph        = None
        self.curr_val_char = None
        self.MacAddr       = None
        self.SN            = SerialNumber
        self.uuid          = UUID("b42e2a68-ade7-11e4-89d3-123b93f75cba")

    def connect(self):
        # Auto-discover device on first connection
        if (self.MacAddr is None):
            scanner     = Scanner().withDelegate(DefaultDelegate())
            searchCount = 0
            while self.MacAddr is None and searchCount < 50:
                devices      = scanner.scan(0.1) # 0.1 seconds scan period
                searchCount += 1
                for dev in devices:
                    ManuData = dev.getValueText(255)
                    SN = parseSerialNumber(ManuData)
                    if (SN == self.SN):
                        self.MacAddr = dev.addr # exits the while loop on next conditional check
                        break # exit for loop
            
            if (self.MacAddr is None):
                print "ERROR: Could not find device."
                print "GUIDE: (1) Please verify the serial number."
                print "       (2) Ensure that the device is advertising."
                print "       (3) Retry connection."
                sys.exit(1)
        
        # Connect to device
        if (self.periph is None):
            self.periph = Peripheral(self.MacAddr)
        if (self.curr_val_char is None):
            self.curr_val_char = self.periph.getCharacteristics(uuid=self.uuid)[0]
        
    def read(self):
        if (self.curr_val_char is None):
            print "ERROR: Devices are not connected."
            sys.exit(1)            
        rawdata = self.curr_val_char.read()
        rawdata = struct.unpack('BBBBHHHHHHHH', rawdata)
        sensors = Sensors()
        sensors.set(rawdata)
        return sensors
    
    def disconnect(self):
        if self.periph is not None:
            self.periph.disconnect()
            self.periph = None
            self.curr_val_char = None

# ===================================
# Class Sensor and sensor definitions
# ===================================

NUMBER_OF_SENSORS               = 7
SENSOR_IDX_HUMIDITY             = 0
SENSOR_IDX_RADON_SHORT_TERM_AVG = 1
SENSOR_IDX_RADON_LONG_TERM_AVG  = 2
SENSOR_IDX_TEMPERATURE          = 3
SENSOR_IDX_REL_ATM_PRESSURE     = 4
SENSOR_IDX_CO2_LVL              = 5
SENSOR_IDX_VOC_LVL              = 6

class Sensors():
    def __init__(self):
        self.sensor_version = None
        self.sensor_data    = [None]*NUMBER_OF_SENSORS
        self.sensor_units   = ["%rH", "Bq/m3", "Bq/m3", "degC", "hPa", "ppm", "ppb"]
    
    def set(self, rawData):
        self.sensor_version = rawData[0]
        if (self.sensor_version == 1):
            self.sensor_data[SENSOR_IDX_HUMIDITY]             = rawData[1]/2.0
            self.sensor_data[SENSOR_IDX_RADON_SHORT_TERM_AVG] = self.conv2radon(rawData[4])
            self.sensor_data[SENSOR_IDX_RADON_LONG_TERM_AVG]  = self.conv2radon(rawData[5])
            self.sensor_data[SENSOR_IDX_TEMPERATURE]          = rawData[6]/100.0
            self.sensor_data[SENSOR_IDX_REL_ATM_PRESSURE]     = rawData[7]/50.0
            self.sensor_data[SENSOR_IDX_CO2_LVL]              = rawData[8]*1.0
            self.sensor_data[SENSOR_IDX_VOC_LVL]              = rawData[9]*1.0
        else:
            print "ERROR: Unknown sensor version.\n"
            print "GUIDE: Contact Airthings for support.\n"
            sys.exit(1)
   
    def conv2radon(self, radon_raw):
        radon = "N/A" # Either invalid measurement, or not available
        if 0 <= radon_raw <= 16383:
            radon  = radon_raw
        return radon

    def getValue(self, sensor_index):
        return self.sensor_data[sensor_index]

    def getUnit(self, sensor_index):
        return self.sensor_units[sensor_index]
        
# ===================================
# Main
# ===================================

while True:
    try:
        #---- Connect to MongoDb ----#
        client = MongoClient("mongodb://user:pw@IP:port/admin") #<-------------- Set your mongoDB credential
        db = client['{}'.format('sensors')]
        write = db['{}'.format('airThingsWavePlus')]
        
        #---- Initialize ----#
        waveplus = WavePlus(SerialNumber)
        
        while True:
            try:
                waveplus.connect()
                
                # read values
                sensors = waveplus.read()

                
                writeData = ({
                'humidity': sensors.getValue(SENSOR_IDX_HUMIDITY),
                'radon_st_avg': sensors.getValue(SENSOR_IDX_RADON_SHORT_TERM_AVG),
                'radon_lt_avg': sensors.getValue(SENSOR_IDX_RADON_LONG_TERM_AVG),
                'temperature': sensors.getValue(SENSOR_IDX_TEMPERATURE),
                'pressure': sensors.getValue(SENSOR_IDX_REL_ATM_PRESSURE),
                'CO2_lvl': sensors.getValue(SENSOR_IDX_CO2_LVL),
                'VOC_lvl': sensors.getValue(SENSOR_IDX_VOC_LVL),
                '_id': datetime.datetime.utcnow(),
                    })
                    
                #Write data to DB
                result = write.insert_one(writeData)
                print("Result writing sensor data to Mongo DB: ", result.acknowledged)
                
                if result.acknowledged==False:
                    time.sleep(5)
                    break
                    
                print('-------------------------\n')

                waveplus.disconnect()
                
                #Wait until next request to read sensor data
                time.sleep(SamplePeriod)
                
            except Exception as e:
                print('Inner error!, Msg: ',e)
                time.sleep(5)
            
    except Exception as e:
        print('Outer error!, Msg: ',e)
        time.sleep(5)
                
    finally:
        waveplus.disconnect()
