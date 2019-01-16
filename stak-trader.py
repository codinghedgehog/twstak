# Simple TradeWars2002 Automatic Keypresser (STAK) - Trade Utility
#
# This is an "intelligent" auto-keyer setup for doing paired port
# trading.  In automatic mode, it will accept two sectors as input,
# and automatically figure out the most valuable commodities to trade
# between the two ports of the sector, if possible.
#
# Note that this requires the user to be saving the terminal output to
# a log file for real-time parsing.
#
# Uses: pyautogui
#

import sys
import re
import os
import pyautogui
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
    global DELAY_CHAR, DELAY, TYPESPEED, FAILSAFE, FAILSAFE_DISTANCE, INPUT_FILE, TRADE_LIMIT, SHIP_HOLDS
    
    selection = None
    while True:
        print()
        print("==== MAIN MENU====")
        print("l)  Set input log file (Currently: {0})".format(INPUT_FILE))
        print("tl) Set trade limit (Default: Stop when {0} turns left.)".format(TRADE_LIMIT))        
        print("at) Auto-trade, NO haggling (CTRL-C to stop)")
        print("tav) Trade Advisor - View")
        print("tas) Trade Advisor - Save to file")
        print()
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
        elif selection == "tl":
            print()
            print("-- Set trade limit --")
            try:
                TRADE_LIMIT = int(input("Stop when this many turns left: "))
            except:
                print("Invalid value (number expected).  Restoring default.")
                TRADE_LIMIT=40
                sleep(1)
            print()
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
                
        elif selection == "at":
            try:                
                auto_trade(False)
            except KeyboardInterrupt:
                print("User aborted trade routine...")
        elif selection == "tav":
            try:
                trade_advisor()
            except KeyboardInterrupt:
                print("User aborted trade advisor...")
        elif selection == "tas":
            try:
                fileName = input("Enter path and filename to save: ")
                try:                    
                    with open(fileName,"w") as outFile:
                        trade_advisor(reportFile=outFile)
                except:
                    print("Unable to open file {0} for writing!".format(fileName))
                
            except KeyboardInterrupt:
                print("User aborted trade advisor...")            
        else:
            print("Unknown selection '{0}'".format(selection))

def get_term_coord():
    input("Without losing focus to this window, move your mouse over the titlebar of the terminal window and press ENTER")
    mouse_x,mouse_y = pyautogui.position()
    return (mouse_x,mouse_y)

def trade_advisor(reportFile=None):
    # Uses Computer Interrogation Mode to get list of explored sectors and port info, and advises
    # which port pairs are available.

    global logfile, CIMPortReportRe

    warpMap = {}
    portDB = {}
    
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

        # For each port, look to see if there are any adjacent ports that have a viable trade flow.
        portsDone = []

        for portSector in portDB.keys():
            # Look for trade routes with adjacent ports.
            port1 = portDB[portSector]
            for adjWarp in warpMap[portSector]:
                if adjWarp in portDB.keys():

                    # Skip if we've done this in one direction already.
                    if [adjWarp,portSector] in portsDone:
                        continue
                    
                    port2 = portDB[adjWarp]
                    
                    # Validate there is a viable commodity trade between the two ports.
                    port1Buys = port1.selling.intersection(port2.buying)
                    port2Buys = port2.selling.intersection(port1.buying)

                    # Report amounts, and track sectors visited to avoid double counting.
                    portsDone.append([port1.sector,port2.sector])
                    portsDone.append([port2.sector,port1.sector])

                    if not port1Buys and not port2Buys:
                        continue
                    else:
                        print("Sector {0} <-> Sector {1}\n".format(port1.sector,port2.sector),file=reportFile)
                        for commodity in port1Buys:
                            if commodity == "Fuel Ore":
                                print("  Fuel Ore (Selling {0}) -> Fuel Ore (Buying {1})".format(port1.oreAmt,port2.oreAmt),file=reportFile)
                            elif commodity == "Organics":
                                print("  Organics (Selling {0}) -> Organics (Buying {1})".format(port1.orgAmt,port2.orgAmt),file=reportFile)
                            elif commodity == "Equipment":
                                print("  Equipment (Selling {0}) -> Equipment (Buying {1})".format(port1.equAmt,port2.equAmt),file=reportFile)

                        for commodity in port2Buys:
                            if commodity == "Fuel Ore":
                                print("  Fuel Ore (Buying {0}) <- Fuel Ore (Selling {1})".format(port1.oreAmt,port2.oreAmt),file=reportFile)
                            elif commodity == "Organics":
                                print("  Organics (Buying {0}) <- Organics (Selling {1})".format(port1.orgAmt,port2.orgAmt),file=reportFile)
                            elif commodity == "Equipment":
                                print("  Equipment (Buying {0}) <- Equipment (Selling {1})".format(port1.equAmt,port2.equAmt),file=reportFile)

                    print("",file=reportFile)
        
        
    except pyautogui.FailSafeException:
        print("** ABORTED: Fail safe triggered.")
        return
    

def auto_trade(negotiate=False):

    # Given two sectors, will query ports and automatically trade the highest valuable commodities
    # that can be bought/sold between the pair.
    
    global TRADE_LIMIT, SHIP_HOLDS, commerceReportRe, logfile

    print()
    print("Be sure your terminal program is logging printable output to {0} before continuing.".format(INPUT_FILE))
    print()

    sector1 = input("Enter first sector (the one you're in): ")
    sector2 = input("Enter the second sector: ")

    x,y = get_term_coord()

    yorn = input("Are you already at main command prompt? y/n ").lower()
    if yorn != "y":
        print("Please be at the main command (NOT Computer) prompt before mapping.")
        return

    try:
        flush_follow()
        
        pyautogui.moveTo(x,y)
        pyautogui.click()

        # Check current sector and turns remaining
    
        pyautogui.typewrite("i")
        result,selfInfo = return_up_to("^Credits ",logfile)

        flush_follow()

        #print(selfInfo)

        selfMatch = re.search("Current Sector +: +(?P<currentSector>[0-9]+)", selfInfo)
        if selfMatch:
            currentSector = selfMatch.group('currentSector')
        else:
            print("Unable to collect selfShip current sector information!")
            return

        selfMatch = re.search("Turns to Warp\s+:\s+(?P<turnsWarp>[0-9]+)", selfInfo)
        if selfMatch:
            turnsWarp = int(selfMatch.group('turnsWarp'))
        else:
            print("Unable to collect selfShip turns per warp information!")
            return

        selfMatch = re.search("Turns left\s+:\s+(?P<turnsLeft>[0-9]+)", selfInfo)
        if selfMatch:
            turnsLeft = int(selfMatch.group('turnsLeft'))
        else:
            print("Unable to collect selfShip turns left information!")
            return

        selfMatch = re.search("Total Holds\s+:\s+(?P<totalHolds>[0-9]+)", selfInfo)
        if selfMatch:
            SHIP_HOLDS = int(selfMatch.group('totalHolds'))
        else:
            print("Unable to collect selfShip turns left information!")
            return


        if currentSector != sector1:
            print("Please have your ship in the starting sector ({0}) before proceeding (you are in sector {1}).".format(sector1,currentSector))
            return

        # Activate computer
        pyautogui.typewrite("c")
        waitfor("^Computer command",logfile)

        # Get Port Reports
        pyautogui.typewrite("r")
        pyautogui.typewrite("{0}\n".format(sector1))
        validPort,port1_info = return_up_to("^Computer command",logfile,unless=["^I have no information"])

        if not validPort:
            print("No port in sector {0}".format(sector1))
            return

        pyautogui.typewrite("r")
        pyautogui.typewrite("{0}\n".format(sector2))
        validPort,port2_info = return_up_to("^Computer command",logfile,unless=["^I have no information"])

        if not validPort:
            print("No port in sector {0}".format(sector2))
            return

        #print(port1_info)
        #print(re.search(commerceReportRe,port1_info,flags=re.DOTALL))
        #print(re.search(commerceReportRe,port2_info,flags=re.DOTALL))
        
        port1Report = re.search(commerceReportRe,port1_info,flags=re.DOTALL)

        if port1Report:
            port1 = Starport(sector1,port1Report)
        else:
            print("Unable to parse port data in sector {0}!".format(sector1))
            return
        
        port2Report = re.search(commerceReportRe,port2_info,flags=re.DOTALL)

        if port2Report:
            port2 = Starport(sector2,port2Report)
        else:
            print("Unable to parse port data in sector {0}!".format(sector2))
            return

        #print(port1)
        #print(port2)

        # Validate there is a viable commodity trade between the two ports.
        port1Buys = port1.selling.intersection(port2.buying)
        port2Buys = port2.selling.intersection(port1.buying)

        print(port1Buys)
        print(port2Buys)

        if not port1Buys and not port2Buys:
            print("There are no viable trade plans between these two ports!")
            return

        # Return to main prompt
        pyautogui.typewrite("q")

        flush_follow()

        # Trade back and forth until depleted.
        while turnsLeft > TRADE_LIMIT:
            
            turnsLeft = turnsLeft - 1

            if turnsLeft <= TRADE_LIMIT:
                print("Turn limit reached.  Auto-trading stopped.")
                return

            # Trade at port 1            
            pyautogui.typewrite("pt")
            
            result,portInfo = return_up_to("You have",logfile,unless=["You don't have anything they want, and they don't have anything you can buy"])
            if result:
                portReport = re.search(commerceReportRe,portInfo,flags=re.DOTALL)
                if portReport:
                    port1.update_inventory(portReport)                    
                else:
                    print("Failed to update port1 inventory!")
                    return
            else:
                print("Port depleted.  Auto-trading stopped.")
                return


            # Verify port 2 still has room to buy from port 1, note that OtherPort
            # inventory is adjusted down by one SHIP_HOLDS worth of quantity, since
            # we would've just sold that much while there.
            noBuys = []
            for commodity in port1Buys:
                if commodity == "Fuel Ore" and port2.oreAmt - SHIP_HOLDS < SHIP_HOLDS:
                    noBuys.append("Fuel Ore")
                    print("Not buying Fuel Ore -- not enough demand at other port")
                    
                if commodity == "Organics" and port2.orgAmt - SHIP_HOLDS < SHIP_HOLDS:
                    noBuys.append("Organics")
                    print("Not buying Organics -- not enough demand at other port")
                    
                if commodity == "Equipment" and port2.equAmt - SHIP_HOLDS < SHIP_HOLDS:                    
                    noBuys.append("Equipment")
                    print("Not buying Equipment -- not enough demand at other port")

            for noBuyCommodity in noBuys:
                port1Buys.remove(noBuyCommodity)

            for commodity in port1Buys:
                if commodity == "Fuel Ore":
                    print("Other port is buying {0} Fuel Ore".format(port2.oreAmt))
                    
                if commodity == "Organics":
                    print("Other port is buying {0} Organics".format(port2.orgAmt))
                    
                if commodity == "Equipment":
                    print("Other port is buying {0} Equipment".format(port2.equAmt))
                

            # Verify there are still commodies to trade, otherwise quit.
            if not port1Buys.intersection(port2.buying) and not port2Buys.intersection(port1.buying):
                print("No more tradable commodities at these ports, in any direction. Stopping auto-trade.")
                return

            if not trade_at_port(port1,port1Buys):
                print("Trade exception encountered. Auto-trading stopped.")
                return
            
            waitfor("^Command",logfile)

            # Move to port2 sector
            print()
            print("===> Moving to sector {0}".format(sector2))
            turnsLeft = turnsLeft - turnsWarp
            if turnsLeft <= TRADE_LIMIT:
                print("Trade limit reached.  Auto-trading stopped.")
                return
            else:
                pyautogui.typewrite("m{0}\n".format(sector2))
                waitfor("^Command",logfile)
            
            # Sell and Buy
            turnsLeft = turnsLeft - 1

            if turnsLeft <= TRADE_LIMIT:
                print("Turn limit reached.  Auto-trading stopped.")
                return

            # Trade at port 2            
            pyautogui.typewrite("pt")

            result,portInfo = return_up_to("You have",logfile,unless=["You don't have anything they want, and they don't have anything you can buy"])
            if result:
                port2Report = re.search(commerceReportRe,portInfo,flags=re.DOTALL)
                if port2Report:
                    port2.update_inventory(port2Report)
                else:
                    print("Failed to update port2 inventory!")
                    return
            else:
                print("Port depleted or we are carrying invalid cargo for this port.  Auto-trading stopped.")
                return

            # Verify port 1 still has room to buy from port 2, note that OtherPort
            # inventory is adjusted down by one SHIP_HOLDS worth of quantity, since
            # we would've just sold that much while there.
            noBuys = []
            for commodity in port2Buys:
                if commodity == "Fuel Ore" and port1.oreAmt - SHIP_HOLDS < SHIP_HOLDS:
                    print("Not buying Fuel Ore -- not enough demand at other port")
                    noBuys.append("Fuel Ore")
                    
                if commodity == "Organics" and port1.orgAmt - SHIP_HOLDS < SHIP_HOLDS:
                    print("Not buying Organics -- not enough demand at other port")
                    noBuys.append("Organics")
                    
                if commodity == "Equipment" and port1.equAmt - SHIP_HOLDS < SHIP_HOLDS:
                    print("Not buying Equipment -- not enough demand at other port")
                    noBuys.append("Equipment")
                    
            for noBuyCommodity in noBuys:
                port2Buys.remove(noBuyCommodity)

            for commodity in port2Buys:
                if commodity == "Fuel Ore":
                    print("Other port is buying {0} Fuel Ore".format(port1.oreAmt))
                    
                if commodity == "Organics":
                    print("Other port is buying {0} Organics".format(port1.orgAmt))
                    
                if commodity == "Equipment":
                    print("Other port is buying {0} Equipment".format(port1.equAmt))

            # Verify there are still commodies to trade, otherwise quit.
            if not port1Buys.intersection(port2.buying) and not port2Buys.intersection(port1.buying):
                print("No more tradable commodities at these ports, in any direction. Stopping auto-trade.")
                return

            if not trade_at_port(port2,port2Buys):
                print("Trade exception encountered. Auto-trading stopped.")
                return

            pyautogui.typewrite("d")
            waitfor("^Command",logfile)

            # Move back to port1 sector
            print()
            print("===> Moving to sector {0}".format(sector1))
            pyautogui.typewrite("m{0}\n".format(sector1))
            
        
        
    except pyautogui.FailSafeException:
        print("** ABORTED: Fail safe triggered.")
        return

# Docks at port and performs trade.
def trade_at_port(port,buys):

    global logfile, SHIP_HOLDS

    print(port)
    
    result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile,unless=["How many holds of (?P<commodity>.+) do you want to sell","Command"])
    # Sell what we have first.
    if not result and query.string.find("do you want to sell") >= 0:
        commodity = query.group('commodity')
        print("Selling {0}".format(commodity))
        pyautogui.typewrite("\n\n")
        
        result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile,unless=["How many holds of (?P<commodity>.+) do you want to sell","Command"])
        if not result and query.string.find("do you want to sell") >= 0:
            commodity = query.group('commodity')
            print("Selling {0}".format(commodity))
            pyautogui.typewrite("\n\n")
            
            result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile,unless=["How many holds of (?P<commodity>.+) do you want to sell","Command"])

            if not result and query.string.find("do you want to sell") >= 0:
                commodity = query.group('commodity')
                print("Selling {0}".format(commodity))
                pyautogui.typewrite("\n\n")
            
    # If port is selling commodities.  If it is a Class 8 (BBB) port, just return, since nothing to buy.
    if buys:
        # Even if we want to buy from port, make sure there is still a full cargo holds worth of inventory to buy!
        noBuys = []
        for commodity in buys:
            if commodity == "Equipment" and port.equAmt < SHIP_HOLDS:
                noBuys.append("Equipment")
            if commodity == "Organics" and port.orgAmt < SHIP_HOLDS:
                noBuys.append("Organics")
            if commodity == "Fuel Ore" and port.oreAmt < SHIP_HOLDS:
                noBuys.append("Fuel Ore")

        for noBuyCommodity in noBuys:
            buys.remove(noBuyCommodity)

        # No more inventory to buy, so quit port.
        if not buys:
            
            print("No more inventory to buy (not enough to fill ship holds).  Quitting port.")
            # Decline purchases from this port.
            if "Fuel Ore" in port.selling and port.oreAmt > 0:
                pyautogui.typewrite("0\n")
            if "Organics" in port.selling and port.orgAmt > 0:
                pyautogui.typewrite("0\n")
            if "Equipment" in port.selling and port.equAmt > 0:
                pyautogui.typewrite("0\n")
            
            return True

        if query:
            currentCommodity = query.group('commodity')
            print("Port offers to sell {0}".format(currentCommodity))
        else:
            print("No commodities offered (is our cargo hold full?).")
            return False
    else:
        print("Nothing to buy in trade plan.  Done.")

        # Decline purchases from this port.
        if "Fuel Ore" in port.selling and port.oreAmt > 0:
            pyautogui.typewrite("0\n")
        if "Organics" in port.selling and port.orgAmt > 0:
            pyautogui.typewrite("0\n")
        if "Equipment" in port.selling and port.equAmt > 0:
            pyautogui.typewrite("0\n")

        return True
            
            
    # Only buy what we can sell at the other port, prioritizing equipment, organics, then ore,
    # but only if there is enough to fill our holds, otherwise decline purchase.
    if "Equipment" in buys:
        if port.equAmt >= SHIP_HOLDS:
            print("We want to buy Equipment and port has {0} left.".format(port.equAmt))
            while currentCommodity != "Equipment":
                pyautogui.typewrite("0\n")
                result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
                currentCommodity = query.group('commodity')

            if currentCommodity == "Equipment":
                pyautogui.typewrite("\n\n")
                return True
            else:
                print("Unexpected commodity offer!")
                return False
        elif port.equAmt > 0:
            result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
            pyautogui.typewrite("0\n")
        
    if "Organics" in buys:
        if port.orgAmt >= SHIP_HOLDS:
            print("We want to buy Organics and port has {0} left.".format(port.orgAmt))
            while currentCommodity != "Organics":
                pyautogui.typewrite("0\n")
                result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
                currentCommodity = query.group('commodity')

            if currentCommodity == "Organics":
                pyautogui.typewrite("\n\n")
                return True
            else:
                print("Unexpected commodity offer!")
                return False
        elif port.orgAmt > 0:
            result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
            pyautogui.typewrite("0\n")
        
    if "Fuel Ore" in buys:
        if port.oreAmt >= SHIP_HOLDS:
            print("We want to buy Fuel Ore and port has {0} left.".format(port.oreAmt))
            while currentCommodity != "Fuel Ore":
                pyautogui.typewrite("0\n")
                result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
                currentCommodity = query.group('commodity')

            if currentCommodity == "Fuel Ore":
                pyautogui.typewrite("\n\n")
                return True
            else:
                print("Unexpected commodity offer!")
                return False
        elif port.oreAmt > 0:
            result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
            pyautogui.typewrite("0\n")

    return True


    

# Saves lines from logfile until a line matches
# either regex, which will return (True,collectedLines),
# or one of the expressions in the "unless" variable,
# in which case it will return (False,collectedLines).
def return_up_to(regex,logfile,unless=[]):
    output = ""
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
    

# Consumes lines from logfile until regex matches and returns (True,MatchObject), or
# if a pattern in the "unless" list of regexes is matched, in which case it returns the
# (False,MatchObject)
def waitfor(regex,logfile,unless=[]):
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

def follow(filename):
    thefile = open(filename,"r")
    thefile.seek(0,2)      # Go to the end of the file
    while True:
        line = thefile.readline()
        if not line:
            sleep(0.1)    # Sleep briefly
            continue
        
        yield line

def flush_follow():
    # Reopens log file and starts following at EOF.
    global INPUT_FILE, logfile
    logfile = follow(INPUT_FILE)

if __name__ == "__main__":

    VERSION="1.3"
    INPUT_FILE="C:\\Temp\\tw2002a.log"
        
    TYPESPEED=0.05
    DELAY_CHAR="`"
    DELAY=1

    FAILSAFE_DISTANCE=10
    FAILSAFE=True

    TRADE_LIMIT=40

    commerceReportRe = "Fuel Ore +(?P<oreStatus>Buying|Selling) +(?P<oreAmt>[0-9]+) .+Organics +(?P<orgStatus>Buying|Selling) +(?P<orgAmt>[0-9]+) .+Equipment +(?P<equStatus>Buying|Selling) +(?P<equAmt>[0-9]+) "

    CIMPortReportRe = "^ +(?P<CIMPortSector>[0-9]+) +(?P<oreStatus>-)? +(?P<oreAmt>[0-9]+) +(?P<orePct>[0-9]+)% +(?P<orgStatus>-)? +(?P<orgAmt>[0-9]+) +(?P<orgPct>[0-9]+)% +(?P<equStatus>-)? +(?P<equAmt>[0-9]+) +(?P<equPct>[0-9]+)%"

    logfile = follow(INPUT_FILE)

    SHIP_HOLDS=85


    print("***** STAK - Trade Tool {0} *****".format(VERSION))
    print()
    do_main_menu()


