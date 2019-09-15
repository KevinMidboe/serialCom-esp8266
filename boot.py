from machine import Pin, I2C
i2c = I2C(scl=Pin(5), sda=Pin(4), freq=100000)

import socket
from time import sleep_ms

html = b"""
<!DOCTYPE html><html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <h1>hello world</h1>
  <button onclick="navigate('toggle')">Toggle Amp</button>
  <button onclick="navigate('down')">Decrease volume</button>
  <button onclick="navigate('up')">Increase volume</button>
  <button onclick="navigate('reset')">Reset volume</button>
  <button onclick="navigate('a1')">Audio 1</button>
  <button onclick="navigate('a2')">Audio 2</button>
  <button onclick="navigate('av1')">AV 1</button>
  <button onclick="navigate('av2')">AV 2</button>
</body>
<script type="text/javascript">
function toggle(value) {
  console.log('posting', value)
  window.fetch('/', {
    method: 'POST',
    body: value
  })
  .then(console.log, console.error)
}
function navigate(value) {
  console.log('navigating', value)
  window.location.replace('/' + value)
}
</script></html>
"""

# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import uos, machine
#uos.dupterm(None, 1) # disable REPL on UART(0)
import gc
#import webrepl
#webrepl.start()
gc.collect()

# - - - NETWORKING - - - 
import network
sta_if = network.WLAN(network.STA_IF)

def connectWifi():
  sta_if.active(True)

  # PSID and password for wifi
  sta_if.connect('', '')
  return sta_if
def disconnectWifi():
  sta_if.active(False)

if not sta_if.isconnected():
  print('connecting to network...')
  connectWifi()
  while not sta_if.isconnected():
    pass
print('network config:', sta_if.ifconfig())

from time import sleep

s = socket.socket()
ai = socket.getaddrinfo("0.0.0.0", 8080)
print("Bind address info:", ai)
addr = ai[0][-1]
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind(addr)
s.listen(5)
print("Listening, connect your browser to http://{}:8080/".format(addr))

class Headers(object):
  def __init__(self, headers):
    self.__dict__.update(headers)

  def __getitem__(self, name):
    return getattr(self, name)

  def get(self, name, default=None):
    return getattr(self, name, default)

class Request(object):
  def __init__(self, sock):
    header_off = -1
    data = ''
    while header_off == -1:
      data += sock.recv(2048).decode('utf-8')
      header_off = data.find('\r\n\r\n')
    header_string = data[:header_off]
    self.content = data[header_off+4:]

    print('data', data)

    # lines = []
    # while len(header_string) > 0:
    #   match = self.header_re.search(header_string)
    #   group = match.group(0)
    #   print('mathc', group)
    #   lines.append(group)
    #   header_string = header_string[len(group) + 2:]
    lines = header_string.split('\r\n')

    first = lines.pop(0)
    self.method, path, protocol = first.split(' ')
    self.headers = Headers(
      (header.split(': ')[0].lower().replace('-', '_'), header.split(': ')[1]) for header in lines
    )
    self.path = path

    if self.method in ['POST', 'PUT']:
      content_length = int(self.headers.get('content_length', 0))
      while len(self.content) < content_length:
        self.content += sock.recv(4096).decode('utf-8')
      
      if self.content == 'on':
        turnOn()
      elif self.content == 'off':
        turnOff()

def toggleAmp():
  print('Toggling amp')
  i2c.writeto(0x30, 'on')

def volumeDown():
  print('Decreasing volume')
  i2c.writeto(0x30, 'down')

def volumeUp():
  print('Increasing volume')
  i2c.writeto(0x30, 'up')

def resetVolume():
  print('Reseting volume')
  i2c.writeto(0x30, 'r')

def setAudioChannel(channel):
  print('Setting to audio channel:', channel)
  i2c.writeto(0x30, 'a' + str(channel))

def setAVChannel(channel):
  print('Setting AV channel:', channel)
  i2c.writeto(0x30, 'av' + str(channel))

while True:
  socket, addr = s.accept()

  print('client connected from', addr)

  req = Request(socket) 
  if req.path == '/toggle':
    toggleAmp()
  elif req.path == '/up':
    volumeUp()
  elif req.path == '/down':
    volumeDown()
  elif req.path == '/reset':
    resetVolume()
  elif req.path == '/a1':
    setAudioChannel(1)
  elif req.path == '/a2':
    setAudioChannel(2)
  elif req.path == '/av1':
    setAVChannel(1)
  elif req.path == '/av2':
    setAVChannel(2)

  if req.method == 'POST':
    print('this was a post')
  print('req', req.path)
  print('content', req.content)

  socket.send(b'HTTP/1.1 200 OK\n\n' + html)
  socket.close()
