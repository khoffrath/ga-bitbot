"""
Mt. Gox Python API v0.01 by Jonas Rudloff
  This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import pycurl

#c!!!!  Changed json import to simplejson to support python2.4 on centos 5
import simplejson as json
	
class ServerError(Exception):
    def __init__(self, ret):
        self.ret = ret
    def __str__(self):
        return "Server error: %s" % self.ret
class UserError(Exception):
    def __init__(self, errmsg):
        self.errmsg = errmsg
    def __str__(self):
        return self.errmsg
        
class Client:
    def __init__(self, username="", password=""):
        self.username = username
        self.password = password
        self.buff = ""
        self.base_url = "https://mtgox.com"
        self.timeout = 15
        
    def perform(self, path, params):
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.POST, 1)                       
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.VERBOSE, 0)
        self.curl.setopt(pycurl.TIMEOUT, self.timeout)
	self.curl.setopt(pycurl.SSL_VERIFYPEER,0) 			#!!!!!!!! THIS IS PROBABLY A VERY BAD THING TO DO
	self.curl.setopt(pycurl.SSL_VERIFYHOST,0)			#!!!!!!!! THIS IS PROBABLY A VERY BAD THING TO DO
        self.buff = ""
        self.curl.setopt(pycurl.WRITEFUNCTION, self._write)
        self.curl.setopt(pycurl.HTTPPOST, params.items())
        url = "%s/%s" % (self.base_url, path)
        self.curl.setopt(pycurl.URL, url)
        self.curl.perform()
        status = self.curl.getinfo(pycurl.HTTP_CODE)
        if status == "OK" or status == 200:
            return self.buff
        else:
            raise ServerError(self.buff)
            
    def _write(self, x):
        self.buff += x
    
    def request(self, path, params):
        ret = json.loads(self.perform(path, params))
        if "error" in ret:
            raise UserError(ret["error"])
        else:
            return ret
    ### the public api
    def get_ticker(self):
        return self.request("code/data/ticker.php", {"dummy":""})["ticker"]  
    def get_depth(self):
        return self.request("code/data/getDepth.php", {"dummy":""})
    def get_trades(self):
        return self.request("/code/data/getTrades.php", {"dummy":""})
    ### the private api

    def get_key(self):
        params = {"name":self.username, "pass":self.password}
        return self.request("code/getKey.php", params)
   
    def get_balance(self):
        params = {"name":self.username, "pass":self.password}
        return self.request("code/getFunds.php", params)
        
    def get_orders(self):
        params = {"name":self.username, "pass":self.password}
        ret = self.request("code/getOrders.php", params)
        return ret["orders"]
        
    def _get_oid(self, amount, price, orders=None):
        if not orders:
            orders = self.get_orders()
        order = filter(lambda x: x["amount"] == amount and x["price"] == price and x, orders)
        #print order
        if order:
            return order[0]#["oid"]
        else:
            return None
            
    def sell_btc(self, amount, price):
        print "selling %s at price %s" % (str(amount), str(price))
        if amount < 0.01:
            print "minimun amount is 0.1btc"
            return 0
        params = {"name":self.username, "pass":self.password, "amount":str(amount), "price":str(price)}
        return self._get_oid(amount, price, self.request("code/sellBTC.php", params)["orders"])
        
    def buy_btc(self, amount, price):
        print "buying %s at price %s" % (str(amount), str(price))
        if amount < 0.01:
            print "minimun amount is 0.1btc"
            return 0
        params = {"name":self.username, "pass":self.password, "amount":str(amount), "price":str(price)}
        return self._get_oid(amount, price, self.request("code/buyBTC.php", params)["orders"])
        
    def _cancel_order(self, oid, typ):
        params = {"name":self.username, "pass":self.password, "oid":str(oid), "type":str(typ)}
        return self.request("code/cancelOrder.php", params)    
        
    def cancel_order(self, oid):
        orders = self.get_orders()
        order = filter(lambda x: x["oid"] == oid, orders)[0]
        return self._cancel_order(order["oid"], order["type"])
        