#This file is for the classes of the communications over different interfaces
#Inficon Ltd. Balzers 9496-LI
#Autor: Benjamin Mitrovic
#--------------------------------Imports-------------------------------------------

from machine import UART, SoftI2C, SoftSPI, RTC
import ntptime
import network
import time

#--------------------------------Declarations-------------------------------------------

class commI2C:  #Class for communication with various devices over I2C
  def __init__(self, _scl, _sda):   #expected are 2 Pin-objects
    self.I2C = SoftI2C(scl=_scl, sda=_sda)  
 


class commSPI:  #Class for communication with various devices over SPI
  def __init__(self, _mosi, _miso, _clk): #expected are 3 Pin-objects
    self.SPI = SoftSPI(sck=_clk, mosi=_mosi, miso=_miso) 




class commUART:   #Class for serial communication
  def __init__(self, id, baud, _rx, _tx, bits=8, parity=None, stop=1): #rx and tx expect an int of the IO nr.
    self.UART = UART(id, baud, bits, parity, stop)
    self.UART.init(rx=_rx, tx=_tx)
  
  def read(self, nB=0): #read all or as many bytes as specified
    if nB == 0:
      return self.UART.read()
    else:
      return self.UART.read(nB) #returns the data or None on timeout
  
  def readinto(self, buffer, nB=0): #read all or as many bytes as specified into the buffer
    if nB == 0:
      return self.UART.readinto(buffer)
    else:
      return self.UART.readinto(buffer, nB) #returns the Number of read bytes or None on timeout
 
  def any(self):  #check available data
    return self.UART.any()  #returns number of bytes
  
  def write(self, message):   #writes a message
    return self.UART.write(message)  #returns number of bytes written or None on timeout
  
  def clear(self):   #clears the rx-Buffer
    while not (self.any() == 0):  #repeats to avoid reading errors
      self.read()   #reads all data out of the buffer
    return True     #returns True on completion


class netTime:    #Class for Time-Communications with ntp server and the internal RTC
  def __init__(self, ssid, pw):
    self.station = network.WLAN(network.STA_IF) #defines the type of connection
    if self.station.isconnected() == True:
      #print("Already connected")
      return
    self.station.active(True)
    self.station.connect(ssid, pw)
    #print("connecting...")
    while self.station.isconnected() == False:   #Programm waits for succesful connection
      pass
    #print("Connection successful")
    #print(self.station.ifconfig())
    
  def SetRTC(self):
    self.rtc = RTC()
    ntptime.settime()

    sec = ntptime.time()  #NTP Server gibt die Zeit in sekunden seit 1/1/1970 0:0:0 an
    timezone_hour = 2     #timezone offset on hours
    timezone_sec = timezone_hour * 3600   #convert offset to seconds
    sec = (sec + timezone_sec) * 1000L  #add timezone offset to current time
    (year, month, day, hours, minutes, seconds, weekday, yearday) = time.localtime(sec//1000)   #Zeit wird in Lesbares Format konvertiert
    self.rtc.datetime((year, month, day, 0, hours, minutes, seconds, 0))    #write the evaluated time to the internal RTC

  def getTimeStamp(self):
    (year, month, day, weekday, hours, minutes, seconds, subseconds) = self.rtc.datetime()  #reads time out of the RTC
    txt = "{Day}/{Month}/{Year}-{Hours}:{Minutes}:{Seconds}  "  #string Formatting to make it readable  
    timeStamp = txt.format(Day = day, Month = month, Year = year, Hours = hours, Minutes = minutes, Seconds = seconds)  #insert data to the string
    return timeStamp      #returns the timestamp as a string





