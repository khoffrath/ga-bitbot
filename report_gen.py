
"""
report_gen v0.01 

report generator

Copyright 2011 Brian Monkaba

This file is part of ga-bitbot.

    ga-bitbot is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ga-bitbot is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ga-bitbot.  If not, see <http://www.gnu.org/licenses/>.
""" 
 
#
#	Generates GA trade simulation reports using the gene server
#	Also calculates & submits the next buy trigger
#

__appversion__ = "0.01a"
print "Genetic Bitcoin Report Generator v%s"%__appversion__
# connect to the xml server
#

import xmlrpclib
import json
import gene_server_config
import time


__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)

#make sure the port number matches the server.
server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)  

print "Connected to",__server__,":",__port__


from bct import *


max_length = 60 * 24 * 360

def load():
    #open the history file
    f = open("./datafeed/bcfeed_mtgoxUSD_1min.csv",'r')
    #f = open("./datafeed/test_data.csv",'r')
    d = f.readlines()
    f.close()
    
    if len(d) > max_length:
	#truncate the dataset
	d [max_length * -1:]

    #load the backtest dataset
    input = []
    for row in d[1:]:
	r = row.split(',')[1] #last price
	t = row.split(',')[0] #time
	input.append([int(float(t)),float(r)])
    return input


while 1:
    print "_" * 80
    print time.ctime()  
    #load the data set
    input = load()
    
    buys = []
    targets = []
    for quartile in [1,2,3,4]:
	    #create the trade engine    
	    te = trade_engine()
	    #get the high score gene from the gene server
	    while 1:
		try:
		    ag = json.loads(server.get(120*5,quartile))
		    break
		except:
		    print "Gene Server Error"
		    time.sleep(10)
	    
	    if type(ag) == type([]):
		ag = ag[0]
	    
	    #THE FOLLOWING SECTION MUST MATCH THE GTS Tool!!!
	    #set the trade engine class vars
	    #te.buy_delay =  len(input) - (60 * 12)
	    te.shares = ag['shares']
	    te.wll = ag['wll'] + ag['wls'] + 2 #add the two together to make sure
					#the macd moving windows dont get inverted
	    te.wls = ag['wls'] + 1
	    te.buy_wait = ag['buy_wait']
	    te.markup = ag['markup'] + (te.commision * 3.0) #+ 0.025
	    te.stop_loss = ag['stop_loss']
	    te.stop_age = ag['stop_age']
	    te.macd_buy_trip = ag['macd_buy_trip'] * -1.0
	    te.buy_wait_after_stop_loss = ag['buy_wait_after_stop_loss']
	    #feed the input through the trade engine
	    
	    #preprocess the data
	    te.classify_market(input)
	    #selecct the quartile to test
	    te.test_quartile(quartile)
	    te.net_worth_log = []

	    #feed the data
	    try:
		for i in input:
		    te.input(i[0],i[1])
	    except:
		print "Gene Fault"
	    else:

		# Calc the next buy trigger point
		if len(te.positions) > 0:
		    target = te.input_log[-1][1] - (((te.macd_pct_log[-1][1] - te.macd_buy_trip) / 100.0) * te.input_log[-1][1]) - 0.001
		    if target > te.input_log[-1][1]:
		    	target = te.input_log[-1][1]

		    te.score()
		    st = input[-1][0] + 2000
		    te.input(st,target)
		    p = te.positions[-1]

		    #te.classify_market(input)

		    te.chart("/home/emfb/public_html/bc/chart.templ","/tmp/chart_test_%s.html"%str(quartile))
		    te.chart("/home/emfb/public_html/bc/chart.templ","/tmp/chart_test_zoom_%s.html"%str(quartile),60*24)
		    #print "Evaluating target price"
		    if (target >= p['buy']) or (abs(target - p['buy']) < 0.01): #submit the order at or below target
			    print "sending target buy order to server.."
			    #format the orders
			    p['buy'] = float("%.3f"%(p['buy'] - 0.01))
			    p['target'] = float("%.3f"%p['target'])
			    p.update({'stop_age':(60 * te.stop_age)})
			    server.put_target(json.dumps(p))
			    print "-" * 40
			    print "Quartile  :",quartile
		    	    print "Buy       :$", p['buy']
		    	    print "Target    :$",p['target']
			    print "Win Ratio :","%.3f"%((te.wins / float(te.wins + te.loss)) * 100),"%"
		    	    print "-" * 40
		    else:
			print "Target out of range, no order set.",abs(target - p['buy'])
			p['buy'] = 0
			p['target'] = 0
		    	server.put_target(json.dumps(p))

		    buys.append(p['buy'])
		    targets.append(p['target'])
    #log the orders
    f = open("/tmp/rg_buys.csv",'a')
    f.write(",".join(map(str,buys)) + ",")
    f.write(",".join(map(str,targets)) + "\n")
    f.close()

    #print "sleeping..."
    print "_" * 80
    print "\n"
    #time.sleep(60) #generate a report every 20 seconds
    
