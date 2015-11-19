#!/usr/bin/python

import requests, json, argparse, sys, datetime

exits = [{"text": "Ok", "code": 0}, {"text": "args.w", "code": 1}, {"text": "Critical", "code": 2}, {"text": "Unknown", "code": 3}]
exit = exits[3]

parser = argparse.ArgumentParser(description='Check for monitoring UBNT Radios')
parser.add_argument('-H', help='UBNT radio address')
parser.add_argument('-s', help='Use SSL',action="store_true")
parser.add_argument('-S', help='Use SSL and ignore certificate warning', action="store_true")
parser.add_argument('-U', help='Username', default="ubnt")
parser.add_argument('-P', help='Password', default="ubnt")
parser.add_argument('-i', help='Signal strength warning:critical default < 70:80', default="70:80")
parser.add_argument('-j', help='CCQ warning:critical default < 80:50', default="80:50")



args = parser.parse_args()

sig_warn = -int(args.i.split(":")[0])
sig_crit = -int(args.i.split(":")[1])
ccq_warn = int(args.j.split(":")[0])
ccq_crit = int(args.j.split(":")[1])

verify_cert = False if args.S else True

message = ""
perfdata = " | "
critical = 0
warning = 0

if args.s or args.S: 
	url = "https://"
else:
	url = "http://"

with requests.Session() as s: 
	postdata = {'username': ('', args.U), 'password': ('', args.P), 'url': ('', 'status.cgi')}
	
	try:
		r = s.get(url + args.H + '/login.cgi', timeout=3,verify=verify_cert)
	except requests.RequestException as e:
		print "UNKNOWN: " + str(e)
		sys.exit(exits[3]["code"])

	r= s.post(url + args.H +'/login.cgi', files=postdata,verify=verify_cert)

	if not len(r.history): 
		print "UNKNOWN: Not redirected to correct resource, possibly login failure"
		sys.exit(exits[3]["code"])

	r= s.post(url + args.H + '/status.cgi',verify=verify_cert)
	values = json.loads(r.text)

	info = "Hostname: " + str(values["host"]["hostname"])
	info += "\nRadio Type: " + str(values["wireless"]["mode"]).title()
	info += "\nUptime: " + str(datetime.timedelta(seconds=values["host"]["uptime"]))
	info += "\nFirmware Vers: " + str(values["host"]["fwversion"])
	info += "\nSSID: " + str(values["wireless"]["essid"]) 

	if(values["host"]["uptime"] < 1200): 
		warning += 1
		message += "Uptime less than 20 mins\n"


	if(values["wireless"]["mode"] == "airfiber"): 
		info += "\nLink Overview: " + values["airfiber"]["linkmode"] + " - " + values["airfiber"]["linkstate"]
		info += "\nfrequency (TX/RX): " + str(values["airfiber"]["tx_frequency"]) + "Mhz/" + str(values["airfiber"]["rx_frequency"]) +"Mhz"
		info += "\nSignal Strength (local/remote): " + str(values["airfiber"]["rxpower0"]) + "," + str(values["airfiber"]["rxpower1"]) + "/" + str(values["airfiber"]["remote_rxpower0"]) + "," + str(values["airfiber"]["remote_rxpower1"])
		info += "\nCapacity (TX/RX): " + str(values["airfiber"]["txcapacity"]/1024/1024) + "Mbps/" + str(values["airfiber"]["rxcapacity"]/1024/1024) + "Mbps"
		info += "\nLink Uptime: " + str(datetime.timedelta(seconds=values["airfiber"]["linkuptime"])) 

		perfdata += "'RX Chain0'=" + str(values["airfiber"]["rxpower0"]) + ";" +  str(sig_warn) + ";" + str(sig_crit) 
		perfdata += " 'RX Chain1'=" + str(values["airfiber"]["rxpower1"]) + ";" +  str(sig_warn) + ";" + str(sig_crit) 
		perfdata += " 'RX Capacity'=" + str(values["airfiber"]["rxcapacity"]/1024/1024)
		perfdata += " 'TX Chain0'=" + str(values["airfiber"]["remote_rxpower0"]) + ";"  + str(sig_warn) + ";" + str(sig_crit)
		perfdata += " 'TX Chain1'=" + str(values["airfiber"]["remote_rxpower1"]) + ";"  + str(sig_warn) + ";" + str(sig_crit)
		perfdata += " 'TX Capacity'=" + str(values["airfiber"]["txcapacity"]/1024/1024)
		
		w = False
		c = False

		for ss in [values["airfiber"]["rxpower0"], values["airfiber"]["rxpower0"], values["airfiber"]["remote_rxpower0"], values["airfiber"]["remote_rxpower0"]]:
			if ss < sig_crit:
				critical += 1
				c = True
			elif ss < sig_warn:
				warning += 1
				w = True
		if c: 
			message += "One or more chains above critical signal threshold of " + str(sig_crit) + "\n"
		elif w:
			message += "One or more chains above warning signal threshold of " + str(sig_warn) + "\n"

	else: 
		info += "\nFrequency: " + str(values["wireless"]["frequency"]) +"Mhz"
		info += "\nChains: " + str(values["wireless"]["chains"])
		info += "\nSignal Strength: " + str(values["wireless"]["signal"])
		info += "\nRSSI: " + str(values["wireless"]["rssi"])
		info += "\nNoise Floor: " + str(values["wireless"]["noisef"])
		info += "\nCCQ: " + str(values["wireless"]["ccq"]/10)
		info += "\nRate (TX/RX): " + str(values["wireless"]["txrate"]) + "Mbps/" + str(values["wireless"]["rxrate"]) + "Mbps"
		info += "\nLink Distance: " + str(values["wireless"]["distance"])
		if "quality" in values["wireless"]["polling"]: 
			info += "\nAirmax Quality: " + str(values["wireless"]["polling"]["quality"]) + "%"
		if "capacity" in values["wireless"]["polling"]:
			info += "\nAirmax Capacity: " + str(values["wireless"]["polling"]["capacity"]) + "%"

		perfdata += "'Signal Strength'=" + str(values["wireless"]["signal"]) + ";" + str(sig_warn) + ";" + str(sig_crit)
		perfdata += " 'Noise Floor'=" + str(values["wireless"]["noisef"]) 
		perfdata += " 'CCQ'=" + str(values["wireless"]["ccq"]/10) + "%;" + str(ccq_warn) + ";" + str(ccq_crit)
		if "quality" in values["wireless"]["polling"]: 
			perfdata += " 'Airmax Quality'=" + str(values["wireless"]["polling"]["quality"]) + "%" 
		if "capacity" in values["wireless"]["polling"]:
			perfdata += " 'Airmax Capacity'=" + str(values["wireless"]["polling"]["capacity"]) + "%"

		if values["wireless"]["signal"] < sig_crit:
			critical += 1
			message += "One or more chains above critical signal threshold of " + str(sig_crit) + "\n"

		elif values["wireless"]["signal"] < sig_warn:
			warning += 1
			message += "One or more chains above warning signal threshold of " + str(sig_warn) + "\n"

		if values["wireless"]["ccq"]/10 < ccq_crit:
			critical += 1
			message += "CCQ below threshold threshold of " + str(ccq_crit) + "\n"

		elif values["wireless"]["ccq"]/10 < ccq_warn:
			warning += 1
			message += "CCQ below threshold of " + str(ccq_warn) + "\n"

	if "gps" in values.keys(): 
		info += "\nLocation: " + str(values["gps"]["lat"]) + ", " + str(values["gps"]["lon"]) + "; Altitude: " + str(int(values["gps"]["alt"])) + "m"

	if critical:
		exit=exits[2]
	elif warning:
		exit=exits[1]
	else:
		exit=exits[0]

print exit["text"] + ": " + message + info + perfdata
sys.exit(exit["code"])


