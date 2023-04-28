#https://www.inficon.com/media/4457/download/TIRA49D1_B_Web.pdf?v=1&inline=true
#This file is for decoding of the Data from the CDG gauge
#Inficon Ltd. Balzers 9496-LI
#Autor: Benjamin Mitrovic
#---------------------------------Imports------------------------------------------


#--------------------------------Declarations-----------------------------------------

class CDGDecoder:
  def __init__(self):
    self.name = "Brot"
  
  def getPrUnit(self, data):    #method to evaluate the pressure unit from data
    value = data[1] & 0x30  #mask out all bits except 4 and 5
    value = value >> 4
    if value == 0:
      return "mbar"
    elif value == 1:
      return "Torr"
    elif value == 2:
      return "Pa"
    else:
      return "U.Err"
  
  def getFSRExp(self, data):  #method to get exponent for fsr factor
    bits03 = data[6] & 0x0F   #fsr is described in Byte 7 low-bits for exp
    
    if bits03 == 0:
      fsrExp = 10 ** -3
    elif bits03 == 1:
      fsrExp = 10 ** -2
    elif bits03 == 2:
      fsrExp = 10 ** -1
    elif bits03 == 3:
      fsrExp = 10 ** 0
    elif bits03 == 4:
      fsrExp = 10 ** 1
    elif bits03 == 5:
      fsrExp = 10 ** 2
    elif bits03 == 6:
      fsrExp = 10 ** 3
    elif bits03 == 7:
      fsrExp = 10 ** 4
    else:
      fsrExp = 1
   
    return fsrExp
  
  def getFSRMan(self, data):  #method to get mantis for fsr factor
    bits47 = data[6] >> 4     #fsr is described in Byte 7 high-bits for mantis
    
    if bits47 == 0:
      fsrMan = 1.0
    elif bits47 == 1:
      fsrMan = 1.1
    elif bits47 == 2:
      fsrMan = 2.0
    elif bits47 == 3:
      fsrMan = 2.5
    elif bits47 == 4:
      fsrMan = 5.0
    elif bits47 == 5:
      fsrMan = 1.14
    elif bits47 == 6:
      fsrMan = 3.0
    else:
      fsrMan = 1
    
    return fsrMan    
  
  def getFSR(self, data):   #method to get the FSR factor for the pressure calculation
    fsrE = self.getFSRExp(data)
    fsrM = self.getFSRMan(data)
    
    return fsrM * fsrE

  def getA(self, data):   #method to get the "a" factor for the pressure calculation
    SeitenNr = data[0]    #describes the type of gauge
    unit = self.getPrUnit(data)   #unit for pressure value
    fsrMan = self.getFSRMan(data)
    
    if (SeitenNr == 2) | (SeitenNr == 3):   #evaluation according to table in the datasheet
      if unit == "mbar":
        if fsrMan == 1.1:
          return 13332
        else:
          return 1.3332        
      elif unit == "Torr":
        if fsrMan == 1.1:
          return 1
        else:
          return 1.0000
      elif unit == "Pa":
        if fsrMan == 1.1:
          return 1
        else:
          return 133.32    
      else:
        return 1
    else:
      return 1
    
    
  
  def getB(self, data):   #method to get the "b" factor for the pressure calculation
    SeitenNr = data[0]    #describes the type of gauge
    unit = self.getPrUnit(data)   #unit for pressure value
    fsrMan = self.getFSRMan(data)
    
    if (SeitenNr == 2) | (SeitenNr == 3):   #evaluation according to table in the datasheet
      if unit == "mbar":
        if fsrMan == 1.1:
          return 26400
        else:
          return 24000        
      elif unit == "Torr":
        if fsrMan == 1.1:
          return 1
        else:
          return 32000
      elif unit == "Pa":
        if fsrMan == 1.1:
          return 1
        else:
          return 24000  
      else:
        return 1
      
    elif SeitenNr == 4:
      return 32767
      
    else:
      return 1
  
  def getPress(self, data):   #method to get the pressure from byte 4 and 5
    value = (data[3] << 8) | data[4]   #byte 4 and 5 get combined to 1 16bit signed Integer
    if value & 0x8000:
      value = -(0x10000 - value)    #negative values of signed integer work with the two's complement
    
    return value

  def decodePr(self, data):    #method to get the pressure valuie from the data, combines all other methods in this file
    a = self.getA(data)
    b = self.getB(data)
    fsr = self.getFSR(data)
    value = self.getPress(data)
    unit = self.getPrUnit(data)
    
    result = value * a / b * fsr  #formula according to the datasheet
    msg = str(result) + " " + str(unit)
    
    return msg  #returning the string of the result + the unit

  def dTemp256(self, data):
    value = (data[5] << 8) | data[6]   #byte 6 and 7 get combined to 1 16bit signed Integer
    if value & 0x8000:
      value = -(0x10000 - value)    #negative values of signed integer work with the two's complement
    
    return value / 256
  
  def dTemp128(self, data):
    value = (data[5] << 8) | data[6]   #byte 6 and 7 get combined to 1 16bit signed Integer
    if value & 0x8000:
      value = -(0x10000 - value)    #negative values of signed integer work with the two's complement
   
    return value / 128
    





