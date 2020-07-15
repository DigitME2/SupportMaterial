#! /usr/bin/python3
# see the following websites for reference
# https://pypi.org/project/paho-mqtt/#client
# https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/overview
import sys
import time

import adafruit_dht # library to talk to a temperature/humidity sensor
import board
import digitalio
import paho.mqtt.client as mqtt

dhtSensorDataPin 	= board.D4 	# GPIO pin 4
switchPin 			= board.D27	
ledPin 				= board.D17

dataBrokerAddress = "192.168.0.4"
dhtSensorIntervalSecs = 5 	# approximate interval between taking readings of the 
							# temperature and humidity. Must be greater than 2.

sensor = adafruit_dht.DHT22(dhtSensorDataPin) 	# although the demo uses an AM2302, 
												# it uses an interface compatible 
												# with a DHT22

switch = digitalio.DigitalInOut(switchPin)
switch.direction = digitalio.Direction.INPUT

led = digitalio.DigitalInOut(ledPin)
led.direction = digitalio.Direction.OUTPUT
led.value = False 

# callback function for the MQTT client when it connects to the data broker.
def on_connect(client, userdata, flags, rc):
	print("Connected with result code {}".format(rc))
	client.subscribe("cmd/ledState")
	
	
# callback for when the MQTT client gets a message
def on_message(client, userdata, msg):
	print("{} {}".format(msg.topic, msg.payload))
	if msg.topic == "cmd/ledState":
		if msg.payload.decode() == "on":
			print("Turning LED on")
			led.value = True
		else:
			print("Turning LED off")
			led.value = False
	
def main():
	client = mqtt.Client()
	client.on_connect = on_connect # define some callback functions
	client.on_message = on_message
	
	client.connect(dataBrokerAddress, 1883, 60) # connect to the data broker
	
	client.loop_start() # start a loop on a background thread to process messages
	
	nextReadingTime = time.time()
	lastSwitchState = None
	
	while(True):
		try:
			# read the temperature/humidity sensor if the required delay has passed
			if time.time() >= nextReadingTime:
				try:
					print("Starting sensor read")
					temperature, humidity = None, None
					temperature = sensor.temperature
					humidity = sensor.humidity
					
					print(temperature)
					print(humidity)
					
					if humidity is not None:
						tempStr = "{:0.1f}".format(temperature)
						humStr  = "{:0.1f}".format(humidity)
						print("Readings: Temperature {} *C, Humidity {}%".format(tempStr, humStr))
						
						client.publish("sensorData/temperature", tempStr)
						client.publish("sensorData/humidity", humStr)
					else:
						print("Error reading sensor")
						
					nextReadingTime = time.time() + dhtSensorIntervalSecs
						
				except RuntimeError as error:
					print(error.args[0])
				
			# read the state of the switch, only publishing if the state has changed
			currSwitchState = switch.value
			if currSwitchState != lastSwitchState:
				if switch.value == True:
					print("switch is closed")
					client.publish("sensorData/switch", "on")
					time.sleep(0.5)
				else:
					print("switch is open")
					client.publish("sensorData/switch", "off")
					time.sleep(0.5)
					
			lastSwitchState = currSwitchState

			time.sleep(0.1)
				
			
		except KeyboardInterrupt: 
			# interrupt execution if Ctrl-c is pressed. Might be different keys on Windows.	
			client.loop_stop()
			sys.exit(0)

main()
