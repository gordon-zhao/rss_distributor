'''
Only tested under Python 2
'''

import BaseHTTPServer, SimpleHTTPServer
import ssl

import urllib2 as urllib
import xml.etree.ElementTree as xmlTree
import time, datetime
import types
import random, string
import json
import threading
import sys

settings = {}

clients = []

httpserver = None
server_thread = None
exitFlag = False

new_tasks = {}
tasks = {}
distributed_rss = {}

rss_templetes = {}
last_rss_update = {}

def uprint(string):
    print(string.encode("gbk", "ignore"))

def dprint(string):
    uprint(u"[" + u"{:%d %b %Y %H:%M:%S}".format(datetime.datetime.now()) + u"] " + unicode(string))

def initialize(path_to_settings):
    # Read in settings
    with open(path_to_settings, "r+") as fsettings:
        global settings
        settings = json.load(fsettings)
    # Dictionary distributed_rss setup
    for client in settings["client_settings"]:
            distributed_rss[client] = {}
            clients.append(client)
            if not settings["path"].has_key(client):
                settings["path"][client] = {}
            for site in settings["subscribe_address"].keys():
                if site in settings["client_settings"][client]["subscribe_to"]:
                    distributed_rss[client][site] = {"tasks":{}, "order":[],"actual_feed":None}
                    if not settings["path"][client].has_key(site):
                        # Generate random passkey
                        settings["path"][client][site] = "/{client}/{passkey}".format(client = client, passkey = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(16)))
                elif not site in settings["client_settings"][client]["subscribe_to"] and site in settings["path"][client]:
                    # Remove the extra path
                    # Will trigger warnings in the generateRSS() and getClientFeed() if mismatch path exists
                    del settings["path"][client][site]
    # Global variables setup
    for site in settings["subscribe_address"].keys():
        tasks[site] = {}
        new_tasks[site] = {}
        rss_templetes[site] = xmlTree.Element(u"rss")
        last_rss_update[site] = time.time()
    # Write the settings back
    with open(path_to_settings, "w+") as fsettings:
        fsettings.write(json.dumps(settings, indent = 4))

def getRSS(address):
    if isinstance(address, dict):
        result = {}
        for site in address.keys():
            result[site] = getRSS(address[site])
        # >> {site_name:content}
    if isinstance(address, (list, tuple)):
        result = {}
        for address_ in address:
            result[address_] = getRSS(address_)
        # >> {site_address:content}
    elif isinstance(address, (str, unicode)):
        dprint(u"getRSS(): Processing {address}...".format(address = address))
        result = urllib.urlopen(urllib.Request(url = address, headers = {"User-Agent":u"Chrome 41.0.2227.1"})).read()
        # >> content
    return result

def parseRSS(site, content, encoding = "UTF-8"):
    if isinstance(site, (list, tuple)):
        for site_ in site:
            parseRSS(site_, content, encoding)
    elif isinstance(site, (str, unicode)):
        if isinstance(content, dict):
            assert content.has_key(site), "parseRSS(): Feed Dict does not contain the required site '{}'!".format(site)
            content = content[site]
        assert isinstance(content, (str, unicode)), "parseRSS(): Feed is not string or unicode instance! Details: {}".format(type(content))
        tree = xmlTree.fromstring(content)
        rss_templetes[site] = xmlTree.Element(u"rss")
        rss_templetes[site].set(u"version",u"2.0")
        new_tasks[site] = {}
        for channel in tree:
            node_channel = xmlTree.SubElement(rss_templetes[site], "channel")
            for element in channel:
                if element.tag == u"item":
                    if element.find(u"title") != None:
                        if element.find(u"title").text in tasks[site]:
                            #uprint(u"Updating {title}".format(title=element.find(u"title").text))
                            # TODO: Check if torrent id changed
                            pass
                        elif not element.find(u"title").text in tasks[site]:
                            uprint(u"Adding {title}".format(title=element.find(u"title").text))
                            new_tasks[site][element.find(u"title").text] = {"xmlObject":element, "size":element.find(u"title").text[element.find(u"title").text.rfind(u"[")+1:element.find(u"title").text.rfind(u"]")-4]}
                        tasks[site][element.find(u"title").text] = {"xmlObject":element, "size":element.find(u"title").text[element.find(u"title").text.rfind(u"[")+1:element.find(u"title").text.rfind(u"]")-4]}
                elif element.tag == u"ttl":
                    xmlTree.SubElement(node_channel, u"ttl").text = unicode(settings["check_interval"])
                elif element.tag == u"pubDate":
                    xmlTree.SubElement(node_channel, u"pubDate").text = u"{:%a, %d %b %Y %H:%M:%S} {timezone}".format(datetime.datetime.now(), timezone = u"+0800")
                elif element.tag == u"generator":
                    xmlTree.SubElement(node_channel, u"generator").text = u"RSS Distributor"
                else:
                    node_channel.append(element)
        #xmlTree.dump(rss_templetes[site])
    return new_tasks

def distributeTask(sites = None, by = "number"):
    if not sites:
        sites = new_tasks.keys()
    if isinstance(by, str):
        updated = []
        if by == "number":
            # Equally distribute tasks from each site to each clients
            for site in sites:
                if new_tasks[site]:
                    updated.append(site)
                elif not new_tasks[site]:
                    dprint(u"Nothing new from {}! qwq".format(site))
                index = 0
                for task in new_tasks[site]:
                    for i in range(len(clients)):
                        print(settings["client_settings"][clients[index%len(clients)]]["subscribe_to"])
                        if site in settings["client_settings"][clients[index%len(clients)]]["subscribe_to"]:
                            dprint(u"Task {task} from {site} is distributed to client {client}".format(task = task, site = site, client = clients[index%len(clients)]))
                            distributed_rss[clients[index%len(clients)]][site]["tasks"][task] = new_tasks[site][task]
                            distributed_rss[clients[index%len(clients)]][site]["order"].append(task)
                            index += 1
                            break
                        else:
                            index +=1
                            i+=1   # Prevent accidentally break in the below code when the last client is found subscribe to that site
                    if i == len(clients):
                        dprint(u"No client subscribe to site {}!".format(site))
                        # Check task dictionary to make sure no overflows take place
                        # New tasks will be added back at next check
                        if len(tasks[site].keys()) > 500:
                            tasks[site] = {}
                        break
        else:
            raise Exception(u"distributeTask(): No such sort method: {}".format(by))
    elif isinstance(by, types.FunctionType):
        by(new_tasks, distributed_rss)

    # Cut the list if too long
    for client in distributed_rss.keys():
        for site in distributed_rss[client].keys():
            if len(distributed_rss[client][site]["order"]) > settings["maximum_items_per_client"]:
                for _ in range(len(distributed_rss[client][site]["order"])-settings["maximum_items_per_client"]):
                    removed_task = distributed_rss[client][site]["order"].pop(0)
                    del distributed_rss[client][site]["tasks"][removed_task]
                    del tasks[site][removed_task]

    return updated

def generateRSS(client, sites=None):
    assert isinstance(client, (list, tuple, str, unicode)), u"generateRSS(): Client type mismatched!"
    if isinstance(client, (list, tuple)):
        for client_ in client:
            generateRSS(client_, sites)
    elif isinstance(client, (str, unicode)):
        if client in distributed_rss and sites:
            if isinstance(sites, (list,tuple)):
                for site in sites:
                    if not site in settings["client_settings"][client]["subscribe_to"]:
                        dprint(u"generateRSS(): Warning: Client {} does not subscribe to Site {}!".format(client, site))
                        continue
                    distributed_rss[client][site]["actual_feed"] = xmlTree.fromstring(xmlTree.tostring(rss_templetes[site]))
                    node_channel = distributed_rss[client][site]["actual_feed"].find("channel")
                    for task in distributed_rss[client][site]["tasks"].keys():
                        node_channel.append(distributed_rss[client][site]["tasks"][task]["xmlObject"])
                    #xmlTree.dump(distributed_rss[client][site]["actual_feed"])
                    dprint(u"generateRSS(): Site {site} generated for {client}!".format(site = site, client = client))
            elif isinstance(sites, (str, unicode)):
                generateRSS(client, [sites])
        elif client in distributed_rss and sites == None:
            generateRSS(client, settings["client_settings"][client]["subscribe_to"])
        elif not client in distributed_rss:
            raise Exception(u"Client {} not found!".format(client))

class RSSRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        context = self.getClientFeed(self.path)
        if context:
            self.send_response(200)
            self.end_headers()
            # Get the raw feed of each client and send it out
            self.wfile.write(context)

    def getClientFeed(self, path):
        global settings
        global distributed_rss
        match = None
        for client in settings["path"].keys():
            for site in settings["path"][client]:
                if path == settings["path"][client][site]:
                    match = (client, site)
        if match:
            print("Client Matched: {}".format(match))
            if distributed_rss.has_key(match[0]):
                if distributed_rss[match[0]].has_key(match[1]):
                    return xmlTree.tostring(distributed_rss[match[0]][match[1]]["actual_feed"], encoding="utf-8")
            dprint(u"getClientFeed(): Cannot find this combination from the system: {}".format(match))
        else:
            print("Warning: Unauthorized Access Detected! Details:\n{client_address} >> {requestline} >> {path}".format(client_address = self.client_address, requestline = self.requestline, path = self.path))
            return None

def main():
    initialize("settings.json")
    parseRSS(settings["subscribe_address"].keys(), getRSS(settings["subscribe_address"]))
    distributeTask()
    generateRSS(clients)
    # Server Thread Setup
    httpserver = BaseHTTPServer.HTTPServer((settings['server_listening_address'],int(settings['server_listening_port'])), RSSRequestHandler)
    httpserver.socket = ssl.wrap_socket(httpserver.socket, certfile=settings['server_cert_path'], server_side=True, ssl_version = ssl.PROTOCOL_TLSv1_2)
    server_thread = threading.Thread(target=httpserver.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    while not exitFlag:
        checked_sites = []
        for site in settings["subscribe_address"]:
            if (settings["check_interval"].has_key(site) and time.time() - last_rss_update[site] > settings["check_interval"][site]) or (not settings["check_interval"].has_key(site) and time.time() - last_rss_update[site] > settings["check_interval"]["DEFAULT"]):
                parseRSS(site, getRSS(settings["subscribe_address"][site]))
                last_rss_update[site] = time.time()
                dprint(u"parseRSS(): Site {site} RSS Feed Received!".format(site = site))
                checked_sites.append(site)
        if checked_sites:
            generateRSS(clients, distributeTask(checked_sites))
        # Calculate the next wake up time
        next_scan = last_rss_update[site] + time.time()   # Just some random large number, dont care about it
        for site in settings["subscribe_address"]:
            if settings["check_interval"].has_key(site) and settings["check_interval"][site] + last_rss_update[site] < next_scan:
                next_scan = settings["check_interval"][site] + last_rss_update[site]
            elif not settings["check_interval"].has_key(site) and settings["check_interval"]["DEFAULT"] + last_rss_update[site] < next_scan:
                next_scan = settings["check_interval"]["DEFAULT"] + last_rss_update[site]
        if abs(next_scan-time.time()) > 2:
            dprint(u"main(): See u again after {}s!".format(abs(next_scan-time.time())))
            time.sleep(abs(next_scan-time.time()))

if __name__ == "__main__":
    try:
        main()
    except:
        print("Unexpected error:", sys.exc_info())
    finally:
        print("Exiting...")
        if httpserver:
            httpserver.shutdown()
            httpserver.server_close()
        if server_thread:
            server_thread.join()
