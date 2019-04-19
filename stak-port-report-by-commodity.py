# Simple TradeWars2002 Automatic Keypresser (STAK) - Trade Utility
#
# This is a simple in-game autokeyer for querying port information
# and listing reports in decreasing amount of commodities BOUGHT by port,
# for the purpose of prioritizing planetary twarp trading.
#
# Note that this requires the user to be saving the terminal output to
# a log file for real-time server response parsing.
#
# Uses: pyautogui, pygtail
#

import sys
import re
import os
import datetime
import pyautogui
from pygtail import Pygtail
from time import sleep


# Takes a match object from commerceReportRe or CIMPortReportRe regex to initialize.
class Starport:    
    
    def __init__(self,sector,commerceReport):

        self.sector = sector

        self.selling = set()
        self.buying = set()

        self.orgAmt = 0
        self.oreAmt = 0
        self.equAmt = 0

        if "CIMPortSector" in commerceReport.groupdict():
            
            if commerceReport.group('oreStatus') != '-':
                self.selling.add("Fuel Ore")
            else:
                self.buying.add("Fuel Ore")

            if commerceReport.group('orgStatus') != '-':
                self.selling.add("Organics")
            else:
                self.buying.add("Organics")
                     
            if commerceReport.group('equStatus') != '-':
                self.selling.add("Equipment")
            else:
                self.buying.add("Equipment")
        else:
            if commerceReport.group('oreStatus') == "Selling":
                self.selling.add("Fuel Ore")
            else:
                self.buying.add("Fuel Ore")

            if commerceReport.group('orgStatus') == "Selling":
                self.selling.add("Organics")
            else:
                self.buying.add("Organics")
                     
            if commerceReport.group('equStatus') == "Selling":
                self.selling.add("Equipment")
            else:
                self.buying.add("Equipment")            

        self.oreAmt = int(commerceReport.group('oreAmt'))
        self.orgAmt = int(commerceReport.group('orgAmt'))
        self.equAmt = int(commerceReport.group('equAmt'))


    def __str__(self):
        return """
        Sector: {5}
        Selling {0}
        Buying {1}
        Ore: {2}
        Organics: {3}
        Equipment: {4}
        """.format(self.selling,self.buying,self.oreAmt,self.orgAmt,self.equAmt,self.sector)

    def update_inventory(self,commerceReport):
        self.oreAmt = int(commerceReport.group('oreAmt'))
        self.orgAmt = int(commerceReport.group('orgAmt'))
        self.equAmt = int(commerceReport.group('equAmt'))
        

def do_main_menu():
    global DELAY_CHAR, DELAY, TYPESPEED, FAILSAFE, INPUT_FILE, TRADE_LIMIT, SHIP_HOLDS, logfile
    
    selection = None
    while True:
        print("==== MAIN MENU====")
        print()
        print("-- Trade Operations --")
        print("l) Set input log file (Currently: {0})".format(INPUT_FILE))
        print("r) Run Report")
        print()
        print("-- Settings --")
        print("b)  Begin following log file [Used for Debugging] (CTRL-C to stop)")
        print("g)  Get next line in log file [Used for Debugging]")
        print("dc) Set macro delay char (Currently: {0})".format(DELAY_CHAR))
        print("dv) Set macro delay char value (Currently: {0} seconds)".format(DELAY))
        print("td) Set inter-character typing delay (Currently: {0} seconds)".format(TYPESPEED))
        print("f)  Toggle FAILSAFE (aborts on mouse move to upper left corner): Currently {0}".format(FAILSAFE))
        print()
        print("q)  Quit")
        print()
        selection = input("Selection: ").lower()

        if selection == "l":
            INPUT_FILE=input("File to monitor: ")
            if not os.path.isfile(INPUT_FILE):
                print("WARNING: File {0} does not exist (yet?).".format(INPUT_FILE))
            else:
                logfile = Pygtail(INPUT_FILE,read_at_end=True, copytruncate = False, offset_file="NUL")
                logfile.readlines() # Skip to end (should already happen, but just in case).
        elif selection == "q" or selection == "Q":
            sys.exit(0)
        elif selection == "dc":
            DELAY_CHAR=str(input("Enter character to represent delay in macro string: "))
        elif selection == "dv":
            DELAY=float(input("Enter value of delay character, in seconds (float value allowed): "))
        elif selection == "td":
            TYPESPEED=float(input("Enter delay between keystrokes, in seconds (float value allowed): "))
        elif selection == "f":
            FAILSAFE = not FAILSAFE
        elif selection == "b":
            print()
            print("CTRL-C to stop")
            print()
            try:
                for line in logfile:
                    print(line)
            except KeyboardInterrupt:
                print()
                print("Stopped following file")
                print()
        elif selection == "g":
            print()
            print(next(logfile))
                
        elif selection == "r":
            try:
                fileName = input("Enter path and filename to save: ")
                
                with open(fileName,"w") as outFile:
                    trade_advisor(reportFile=outFile)
                
            except KeyboardInterrupt:
                print("User aborted trade advisor...")
            except PermissionError:
                print("Access denied opening report file for writing...")
            except IOError:
                print("I/O Error encountered (check report/log file path and permissions)...")
        else:
            print("Unknown selection '{0}'".format(selection))

def get_term_coord():
    input("Without losing focus to this window, move your mouse over the titlebar of the terminal window and press ENTER")
    mouse_x,mouse_y = pyautogui.position()
    return (mouse_x,mouse_y)

def trade_advisor(reportFile=None):
    
    # Uses Computer Interrogation Mode to get list of explored sectors and port info, and advises
    # which port pairs are available.

    global logfile, CIMPortReportRe, TRADE_PAIRS

    warpMap = {}
    portDB = {}
    TRADE_PAIRS = []
    
    print()
    print("Be sure your terminal program is logging printable output to {0} before continuing.".format(INPUT_FILE))
    print()

    x,y = get_term_coord()

    yorn = input("Are you already at main command prompt? y/n ").lower()
    if yorn != "y":
        print("Please be at the main command (NOT Computer) prompt before mapping.")
        return

    try:
        flush_follow()
        
        # Enter Computer Interrogation Mode
        pyautogui.moveTo(x,y)
        pyautogui.click()
        
        pyautogui.typewrite("^")
        waitfor("^:",logfile)

        # Create map of known universe, using Warp Display.
        pyautogui.typewrite("i")
        result,rawData = return_up_to("^:",logfile)

        #print("Raw warp data")
        #print(rawData)
        
        rawDataList = rawData.split('\n')
        for line in rawDataList:
            lineMatch = re.search("^ +(?P<sector>[0-9]+) +(?P<warps>.+)",line)
            if lineMatch:
                warpMap[lineMatch.group('sector')] = lineMatch.group('warps').split()
            
        #print(warpMap)

        # Load port report
        pyautogui.typewrite("r")
        result,rawData = return_up_to("^:",logfile)

        #print("Raw port data")
        #print(rawData)
        
        rawDataList = rawData.split('\n')
        for line in rawDataList:
            lineMatch = re.search(CIMPortReportRe,line)
            if lineMatch:
                portDB[lineMatch.group('CIMPortSector')] = Starport(lineMatch.group('CIMPortSector'),lineMatch)
            
        #for item in portDB.values():
        #    print(item)

        # Quit Computer Interrogation Mode.
        pyautogui.typewrite("q")

        # Print out report in order of commodity being purchased, by each commodity
        print("Report generated on {0}".format(datetime.datetime.strftime(datetime.datetime.today(),"%m/%d/%Y %H:%M:%S")),file=reportFile)
        print("",file=reportFile)

        print("",file=reportFile)
        print("=== BY EQUIPMENT ===",file=reportFile)
        print("",file=reportFile)
        print_port_list_order_by_commodity(portDB,"Equipment",reportFile)

        print("",file=reportFile)
        print("",file=reportFile)
        print("=== BY ORGANICS ===",file=reportFile)
        print("",file=reportFile)
        print_port_list_order_by_commodity(portDB,"Organics",reportFile)
        
        print("",file=reportFile)
        print("",file=reportFile)
        print("=== BY FUEL ORE ===",file=reportFile)
        print("",file=reportFile)
        print_port_list_order_by_commodity(portDB,"Fuel Ore",reportFile)

        print("",file=reportFile)
        print("Done.")
        
        
    except pyautogui.FailSafeException:
        print("** ABORTED: Fail safe triggered.")
        return

def print_port_list_order_by_commodity(portDict,portCommodity,reportFile):

    if portCommodity == "Fuel Ore":
        commAmt = "oreAmt"
    elif portCommodity == "Organics":
        commAmt = "orgAmt"
    elif portCommodity == "Equipment":
        commAmt = "equAmt"
    else:
        raise Exception("Invalid portCommodity parameter {0}".format(portCommodity))

    #print(portDict)
    
    sortedPortList = sorted(portDict.values(),key=lambda x: getattr(x,commAmt), reverse=True)
    
    for port in sortedPortList:        
        if portCommodity in port.buying:
            print("",file=reportFile)
            print("Sector {0}".format(port.sector),file=reportFile)
            print("  Buying {0} units of {1}".format(getattr(port,commAmt),portCommodity),file=reportFile)    

# Saves lines from logfile until a line matches
# either the regex parameter, which will return (True,output),
# or one of the expressions in the "unless" list variable,
# in which case it will return (False,output).
def return_up_to(regex,logfile,unless=[]):
    output = ""
    while True:
        for line in logfile:
            
            output = output + line
            
            #print("Checking {0} for {1}".format(line, regex))
            #print(re.search(regex,line))

            # Check exceptions
            for unlessPattern in unless:            
                if  re.search(unlessPattern,line):
                    return (False,output)
            
            if re.search(regex,line):
                return (True,output)
        sleep(0.1)
    

# Consumes lines from logfile until regex matches and returns (True,MatchObject), or
# if a pattern in the "unless" list of regexes is matched, it returns the
# (False,MatchObject) tuple instead.
def waitfor(regex,logfile,unless=[]):
    while True:
        for line in logfile:
            #print("read {0}".format(line))
            #print("Checking {0} for {1}".format(line, regex))
            #print(re.search(regex,line))
            regexMatch = re.search(regex,line)
            if regexMatch:
                return (True,regexMatch)

            # Check exceptions
            for unlessPattern in unless:
                #print("Checking {0} for {1}".format(line, unlessPattern))
                #print(re.search(regex,line))
                
                regexMatch = re.search(unlessPattern,line)
                if regexMatch:
                    return (False,regexMatch)
        sleep(0.1)

def flush_follow():
    # Reopens log file and starts following at EOF.
    global INPUT_FILE, logfile    
    logfile.readlines()

if __name__ == "__main__":

    VERSION="2.0"
    INPUT_FILE="C:\\temp\\tw2002a.log"
        
    TYPESPEED=0.05
    DELAY_CHAR="`"
    DELAY=1

    FAILSAFE=True

    TRADE_LIMIT=40

    # Holds a list of TradePairs
    TRADE_PAIRS = []

    commerceReportRe = "Fuel Ore +(?P<oreStatus>Buying|Selling) +(?P<oreAmt>[0-9]+) .+Organics +(?P<orgStatus>Buying|Selling) +(?P<orgAmt>[0-9]+) .+Equipment +(?P<equStatus>Buying|Selling) +(?P<equAmt>[0-9]+) "

    CIMPortReportRe = "^ +(?P<CIMPortSector>[0-9]+) +(?P<oreStatus>-)? +(?P<oreAmt>[0-9]+) +(?P<orePct>[0-9]+)% +(?P<orgStatus>-)? +(?P<orgAmt>[0-9]+) +(?P<orgPct>[0-9]+)% +(?P<equStatus>-)? +(?P<equAmt>[0-9]+) +(?P<equPct>[0-9]+)%"

    # Note, we pass NUL a the filename to Pygtail because we DON'T want a persistent offset file,
    # we want Pygtail to always start at the end of the terminal log file.  This is especially
    # important if the log file is overwritten with each new session.
    logfile = Pygtail(INPUT_FILE,read_from_end = True, copytruncate = False, offset_file = "NUL")
    logfile.readlines()

    SHIP_HOLDS=50 # This will be updated once we get selfShip info later.


    print("***** STAK - Trade Tool {0} *****".format(VERSION))
    print()
    do_main_menu()


