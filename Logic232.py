#This code is for the Logic232 Datalogger
#Inficon Ltd. Balzers 9496-LI
#Autor: Benjamin Mitrovic
#----------------------------------Imports-----------------------------------------

from machine import Pin
import time
import ssd1306
import proCom
import CDGFormula
import sdcard
import uos

#----------------------------------Classes-----------------------------------------

class Button:   #in this case a switch
  def __init__(self, pin):  #all parameters expect a Pin Object
    self.pin = pin

  def value(self): #returns the logic level of the switch
    return self.pin.value()

class OLED: #requires the display to be driven by an ssd1306 chip
  def __init__(self, _scl, _sda, _height, _width):  
    self.cI2C = proCom.commI2C(_scl, _sda)
    self.display = ssd1306.SSD1306_I2C(width=_width, height=_height, i2c=self.cI2C.I2C)

  def text(self, string, x, y):
    self.display.text(string, x, y)
  
  def fill(self):
    self.display.fill(0)
  
  def show(self):
    self.display.show()

class SDCardModule: #SD-cards communicate over the spi protocoll
  def __init__(self, _cd, _mosi, _miso, _clk, _cs):  #All parameters expect a Pin Object
    self.cSPI = proCom.commSPI(_mosi, _miso, _clk)
    self.cs = _cs
    self.sd = sdcard.SDCard(self.cSPI.SPI, self.cs)
    self.cd = _cd
  
  def log(self, data, timestamp): 
    filename = '/logger/log.txt'
    with open(filename, 'a') as f:
      f.write(timestamp)
      f.write(data)
      f.write('\n')

class CDGSensor:  #class for the CDG connected via RS232C
  def __init__(self, id, baud, _rx, _tx):  
    self.cUART = proCom.commUART(id, baud, _rx, _tx)
    self.temp = 0
    self.atm = 0
    self.pressure = 0
    self.hb = 0
    self.aout = 0
    self.toggler = 0
  
  def read(self, nB=0):         #UART read funtion, reads specified amount of characters
    return self.cUART.read(nB)  

  def any(self):            #scans if there is any available data
    return self.cUART.any()
  
  def write(self, msg):     #writes message to the UART bus
    return self.cUART.write(msg)
  
  def clear(self):        #clears the rx buffer
    return self.cUART.clear()
  
  def readMessage(self):
    first_byte = self.read(1)  #read only 1 byte of the 9-byte message
    if first_byte == b'\x07': #compare the first byte to the start of the documentet message
      buffer = self.read(8)  #read the remaining 8-bytes of the message
      
      sum = buffer[0] + buffer[1] + buffer[2] + buffer[3] + buffer[4] + buffer[5] + buffer[6] #calculate the checksum for validation
      checksum = sum & 0x00FF   #reduce checksum to 1 byte
      if buffer[7] == checksum:   #validate message via Checksum
        return buffer
      else:
        return None
  
  def forceRead(self, command):     #waits for an answer
    while True:  
      self.write(command)       #changing the mode of the gauge for the specified datapoint
      time.sleep(0.05)
      self.clear()            #clearing buffer
      while True:
        first_byte = self.read(1)  #Read only 1 byte of the 9-byte message
        if first_byte == b'\x07': #compare the first byte to the start of the documentet message
          buffer = self.read(8)  #read the remaining 8-bytes of the message
          
          sum = buffer[0] + buffer[1] + buffer[2] + buffer[3] + buffer[4] + buffer[5] + buffer[6] #calculate the checksum for validation
          checksum = sum & 0x00FF   #reduce checksum to 1 byte       
          if buffer[7] == checksum:   #validate message via Checksum
            
            if (buffer[1] & 0x08) != self.toggler:  #checking if toggle bit changed
              self.toggler = buffer[1] & 0x08      
              return buffer
            else: 
              break       #exiting the second loop
        time.sleep(0.005)
      time.sleep(0.005)
 
  def setToggle(self, msg):   #setting the togglebit
    if msg is not None:
      self.toggler = msg[1] & 0x08    #toggle bit is bit 3 of byte 2 in the message
      return True
    return False

#---------------------------objects and variables-----------------------------------------
 
logSwitch = Button(Pin(26, Pin.IN))   #switch to start/stopp the logging function
TempSwitch = Button(Pin(10, Pin.IN))  #switch to start/stopp Temperature Readings

myCDG = CDGSensor(1, 9600, 16, 17)     #object for vacuum gauge
SDCard = None
netClock = None

led = Pin(2, Pin.OUT) #onboard debug LED
CDGDecoder = CDGFormula.CDGDecoder()  #calculations for pressure readings

logCounter = 50   #logging speed: cycleTime * logCounter
cycleTime = 0.07 #cycle time of programm in seconds
doLog = False #bool to activate logging
logCache = logCounter #cache logging timer

RS_STANDARD = bytes([0x03, 0x10, 0x31, 0x00, 0x41])     #command to switch to temperaure mode
CAL_TEMP = bytes([0x03, 0x10, 0x31, 0x01, 0x42])        #""  
CAL_ATM = bytes([0x03, 0x10, 0x31, 0x02, 0x43])         #""
HEATBLOCK_TEMP = bytes([0x03, 0x10, 0x31, 0x04, 0x45])  #""
ANALOG_OUT = bytes([0x03, 0x10, 0x31, 0x03, 0x44])      #""

while True: #loop to initialise Display  
  led.value(1)    #error blinker
  time.sleep(0.5)
  led.value(0)  
  try:
    Display = OLED(_scl=Pin(22), _sda=Pin(21), _height=64, _width=128)  #initalising display
    Display.fill()
    Display.text("Hello!", 0, 0)  #show after initialising
    Display.show()
    break
  except:
    Display = None
    
  time.sleep(0.5)

#---------------------------------start of program-----------------------------------------------------------
  
while True:     #main loop
  led.value(1)    #runtime blinker
  time.sleep(0.1)
  led.value(0)
  
  if logSwitch.value():    
    while SDCard == None:   #Loop to initaliase the sdcard
      led.value(1)    #Blinking LED if Hardware-Error
      time.sleep(0.1)
      led.value(0)
      try:
        SDCard = SDCardModule(_cd=Pin(27, Pin.IN), _mosi=Pin(23), _miso=Pin(19), _clk=Pin(18), _cs=Pin(9))  #Creating SDCard Module
        try:
          uos.mount(SDCard.sd, '/logger') #Append the sdcard to the file system
          Display.fill()
          Display.text("mounted", 0, 0) #Display message on screen for Error Detection
          Display.show()
          time.sleep(0.5)
        except OSError as e:  #error catching to avoid freeze
          Display.fill()
          Display.text("mount failed! \n" + str(e), 0, 0) #Display message on screen for Error Detection
          Display.show()
          time.sleep(0.5)
      except OSError as er:   #error catching to avoid freeze
        Display.fill()
        Display.text("sd fail! " + str(er), 0, 0) #Display message on screen for Error Detection
        Display.show()
        time.sleep(0.5)
        SDCard = None
      
      if not logSwitch.value():  #break the initialising loop, if logging gets turned off
        break
    
    while netClock == None:
      try:
        netClock = proCom.netTime("INFICON-Guest", "") #WLAN connection for timestamp
        netClock.SetRTC()
      except OSError as e:    #error catching to avoid freeze
        Display.fill()
        Display.text("Network Error:", 0, 0)  
        Display.text(str(e), 0, 16)
        Display.show()
        time.sleep(0.5)
        netClock = None
    
    if TempSwitch.value():
      logCache = logCache - 10    #faster countdown to compensate extra runtime
    else:
      logCache = logCache - 1   #counter for logging interval
    
    if logCache < 11:   
      doLog = True     #start logging
      logCache = logCounter #reset counter
  
  try:
    Display.fill()  #clears the display
    
    if not TempSwitch.value():
      Display.text("P", 120, 48)  #symbol to signal pressure mode
      
      if myCDG.any() == 0:  #check for available data 
        Display.text("no Data", 0, 0) #display if no data is available
        
      else:
          
        buffer = myCDG.readMessage() #pressure readings
        if buffer is not None:    #to avoid errors

          myCDG.pressure = CDGDecoder.decodePr(buffer) #calculate pressure reading from byte-message
          
          if doLog:  #check for logging counter
            try:
              SDCard.log(netClock.getTimeStamp(), str(myCDG.pressure)) #logging to sdcard
              doLog = False   #finish logging
            except OSError as e:    #error catching to avoid freeze
              Display.text(str(e), 64, 48)   #flash error message on display
              Display.show()
              time.sleep(3)
       
      Display.text(str(myCDG.pressure), 0, 0)   #always display last saved presssure value
     
    else:
      Display.text("T", 120, 48)    #symbol to display temperature mode
      
      logString = ""
   
      if not (myCDG.any() == 0): #check for available data to avoid errors
        myCDG.clear()   #always reset the buffer!!
        myCDG.setToggle(myCDG.readMessage()) #get toggle bit before reading
        myCDG.clear()   #always reset the buffer!!
        obuffer = myCDG.forceRead(ANALOG_OUT)   #get specified temperature readings
        
        if obuffer is not None:
          myCDG.aout = CDGDecoder.dTemp256(obuffer) #calculate pressure reading from byte-message 
        
      Display.text("A OUT: " + str(myCDG.aout), 0, 0)
      logString = logString + "ANALOG: " + str(myCDG.aout)  #add to the logstring
      
      if not (myCDG.any() == 0):    #check for available data to avoid errors
        myCDG.clear()     #always reset the buffer!!
        myCDG.setToggle(myCDG.readMessage())
        myCDG.clear()   #always reset the buffer!!
        Tbuffer = myCDG.forceRead(CAL_TEMP)   #get specified temperature readings
        if Tbuffer is not None:
          myCDG.temp = CDGDecoder.dTemp256(Tbuffer)   #convert to readable format
        
      Display.text("TEMP: " + str(myCDG.temp), 0, 16)
      logString = logString + ", TEMP: " + str(myCDG.temp)    #add to the logstring
      
      if not (myCDG.any() == 0):    #check for available data to avoid errors
        myCDG.clear()     #always reset the buffer!!
        myCDG.setToggle(myCDG.readMessage())    #get toggle bit before reading
        myCDG.clear()     #always reset the buffer!!
        Abuffer = myCDG.forceRead(CAL_ATM)    #get specified temperature readings
        if Abuffer is not None:
          myCDG.atm = CDGDecoder.dTemp256(Abuffer)    #convert to readable format
        
      Display.text("ATM: " + str(myCDG.atm), 0, 32)
      logString = logString + ", ATM: " + str(myCDG.atm)    #add to the logstring

      if not (myCDG.any() == 0):    #check for available data to avoid errors
        myCDG.clear()     #always reset the buffer!!
        myCDG.setToggle(myCDG.readMessage())    #get toggle bit before reading
        myCDG.clear()     #always reset the buffer!!
        hbuffer = myCDG.forceRead(HEATBLOCK_TEMP)   #get specified temperature readings
        if hbuffer is not None:
          myCDG.hb = CDGDecoder.dTemp128(hbuffer)   #convert to readable format
        
      Display.text("HB: " + str(myCDG.hb), 0, 48)
      logString = logString + ", HB: " + str(myCDG.hb)    #add to the logstring
      
      if not (myCDG.any() == 0):    #check for available data to avoid errors
        myCDG.clear()     #always reset the buffer!!
        myCDG.setToggle(myCDG.readMessage())   #get toggle bit before reading
        myCDG.clear()     #always reset the buffer!!
        pbuffer = myCDG.forceRead(RS_STANDARD)    #get pressure readings
        if pbuffer is not None:
          myCDG.pressure = CDGDecoder.dTemp128(pbuffer) #decode into readable format
        
      logString = logString + ", PRESSURE: " + str(myCDG.pressure) #add to the logstring
      
      if doLog:  #check for logging counter
        try:
          SDCard.log(netClock.getTimeStamp(), logString) #logging to sdcard
          doLog = False   #finish logging
          Display.text("log", 80, 48)   #flash message on the display
        except:
          Display.text("log Err", 64, 48)   #flash error message on display
          Display.show()
          time.sleep(3)
      
      myCDG.write(RS_STANDARD)   #reset mode to standart
      myCDG.clear()     #always reset the buffer!!
      
  except OSError as e:    #error catching to avoid freeze
    Display.fill()
    Display.text(str(e), 0, 0)
    
  Display.show()          #general display output (EVA)
  time.sleep(cycleTime)   #runtime cycle delay
  









