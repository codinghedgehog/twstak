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
# Uses: pyautogui, pygtail
#

import sys
import re
import os
import datetime
import pyautogui
from pygtail import Pygtail
from time import sleep


class TradePair:

    def __init__(self,port1,port2):

        self.port1 = port1
        self.port2 = port2

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
                
                with open(fileName,"w") as outFile:
                    trade_advisor(reportFile=outFile)
                
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

    global logfile, CIMPortReportRe, TRADE_PAIRS

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

                    # Validate that the second port sector can warp BACK to the first sector,
                    # since not all warps are two-directional in Tradewars.
                    if not portSector in warpMap[adjWarp]:
                        continue
                    
                    # Validate there is a viable commodity to trade between the two ports.
                    port1Buys = port1.selling.intersection(port2.buying)
                    port2Buys = port2.selling.intersection(port1.buying)

                    # Report amounts, and track sectors visited to avoid double counting.
                    portsDone.append([port1.sector,port2.sector])
                    portsDone.append([port2.sector,port1.sector])

                    if not port1Buys and not port2Buys:
                        continue
                    else:
                        TRADE_PAIRS.append(TradePair(port1,port2))

        # Grade port trading pairs (A, B, C, D)
        #
        # Definition of graded port (from lowest to highest, inclusive of lower grade requirements):
        # D. Default priority, can trade at least one commdity in one direction.
        # C. All tradable Commodity amounts > 1000
        # B. Bidirectional trading with at least two commodities
        # A. Bidirection trading with Org and Equ specifically.
        D_LIST = []
        C_LIST = []
        B_LIST = []
        A_LIST = []

        for portPair in TRADE_PAIRS:
            
            port1Buys = portPair.port1.selling.intersection(portPair.port2.buying)
            port2Buys = portPair.port2.selling.intersection(portPair.port1.buying)

            graded = False

            # Populate D list (filter out ports with low inventory).
            for commodity in port1Buys:

                if graded:
                    break
                
                if commodity == 'Fuel Ore' and (int(portPair.port1.oreAmt) < 1000 or int(portPair.port2.oreAmt) < 1000): 
                    D_LIST.append(portPair)
                    graded = True
                    continue
                elif commodity == 'Organics' and (int(portPair.port1.orgAmt < 1000) or int(portPair.port2.orgAmt) < 1000):
                    D_LIST.append(portPair)                    
                    graded = True
                    continue
                elif commodity == 'Equipment' and (int(portPair.port1.equAmt) < 1000 or int(portPair.port2.equAmt) < 1000):
                    D_LIST.append(portPair)
                    graded = True
                    continue

            if graded:
                continue

            for commodity in port2Buys:

                if graded:
                    break
                
                if commodity == 'Fuel Ore' and (int(portPair.port2.oreAmt) < 1000 or int(portPair.port1.oreAmt) < 1000):
                    D_LIST.append(portPair)
                    graded = True
                    continue
                elif commodity == 'Organics' and (int(portPair.port2.orgAmt) < 1000 or int(portPair.port1.orgAmt) < 1000):
                    D_LIST.append(portPair)
                    graded = True
                    continue
                elif commodity == 'Equipment' and (int(portPair.port2.equAmt) < 1000 or int(portPair.port1.equAmt) < 1000):
                    D_LIST.append(portPair)
                    graded = True
                    continue
                
            if graded:
                continue
                
            # Populate C list (filter out uni-directional trading pairs)
            if not port1Buys or not port2Buys:
                C_LIST.append(portPair)
                continue

            # Populate A & B lists
            if 'Equipment' in port1Buys and 'Organics' in port2Buys:
                A_LIST.append(portPair)
            elif 'Organics' in port1Buys and 'Equipment' in port2Buys:
                A_LIST.append(portPair)
            else:
                B_LIST.append(portPair)

        # Print out report in order of priority
        print("Report generated on {0}".format(datetime.datetime.strftime(datetime.datetime.today(),"%m/%d/%Y %H:%M:%S")),file=reportFile)
        print("",file=reportFile)

        print("=== GRADE A TRADE ROUTES ===",file=reportFile)
        print("",file=reportFile)
        print_port_pair_trade_list(A_LIST,reportFile)

        print("",file=reportFile)
        print("=== GRADE B TRADE ROUTES ===",file=reportFile)
        print("",file=reportFile)
        print_port_pair_trade_list(B_LIST,reportFile)
        
        print("",file=reportFile)
        print("=== GRADE C TRADE ROUTES ===",file=reportFile)
        print("",file=reportFile)
        print_port_pair_trade_list(C_LIST,reportFile)

        print("",file=reportFile)
        print("=== GRADE D TRADE ROUTES ===",file=reportFile)
        print("",file=reportFile)
        print_port_pair_trade_list(D_LIST,reportFile)

        print("",file=reportFile)
        print("Done.")
        
        
    except pyautogui.FailSafeException:
        print("** ABORTED: Fail safe triggered.")
        return

def print_port_pair_trade_list(portPairList,reportFile):
    
    for portPair in portPairList:
        port1 = portPair.port1
        port2 = portPair.port2

        port1Buys = portPair.port1.selling.intersection(portPair.port2.buying)
        port2Buys = portPair.port2.selling.intersection(portPair.port1.buying)

        print("",file=reportFile)
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

    yorn = input("Are you already at the main command prompt? y/n ").lower()
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

        # Verify ports are adjacent to each other.
        pyautogui.typewrite("i{0}\n".format(sector1))
        result,sectorWarps = waitfor("sector\(s\) : +(?P<warpLanes>.+)$",logfile,unless=["^You have never visited sector"])
        if result and sector2 not in sectorWarps.group('warpLanes').split(' - '):
            print("{0} and {1} are not adjacent sectors.".format(sector1, sector2))
            return

        waitfor("^Computer command",logfile)
        
        pyautogui.typewrite("i{0}\n".format(sector2))
        result,sectorWarps = waitfor("sector\(s\) : +(?P<warpLanes>.+)$",logfile,unless=["^You have never visited sector"])
        if result and sector1 not in sectorWarps.group('warpLanes').split(' - '):
            print("{0} and {1} are not adjacent sectors.".format(sector1, sector2))
            return

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

        print(port1)
        print(port2)

        # Validate there is a viable commodity trade between the two ports.
        port1Buys = port1.selling.intersection(port2.buying)
        port2Buys = port2.selling.intersection(port1.buying)

        #print(port1Buys)
        #print(port2Buys)

        if not port1Buys and not port2Buys:
            print("There are no viable trade plans between these two ports!")
            return
        
        # Return to main prompt
        pyautogui.typewrite("q")

        flush_follow()

        # Trade back and forth until depleted or trade limit is hit.
        currentSector = sector1
        currentPort = port1
        currentBuys = port1Buys
        otherSector = sector2
        otherPort = port2
        otherBuys = port2Buys
        while turnsLeft > TRADE_LIMIT:

            print("Docking...")
            turnsLeft = turnsLeft - 1
            print("{0} turns left.".format(turnsLeft))

            if turnsLeft <= TRADE_LIMIT:
                print("Turn limit reached.  Auto-trading stopped.")
                return

            # Trade at current port.            
            pyautogui.typewrite("pt")
            
            result,portInfo = return_up_to("You have",logfile,unless=["You don't have anything they want, and they don't have anything you can buy"])            
            if result:
                portReport = re.search(commerceReportRe,portInfo,flags=re.DOTALL)
                if portReport:
                    currentPort.update_inventory(portReport)                    
                else:
                    print("Failed to update port inventory in sector {0}!".format(currentSector))
                    return
            else:
                print("Nothing to buy or sell.  Port depleted?  Auto-trading stopped.")
                return

            # Verify other port still has room to buy from current port, note that OtherPort
            # inventory is adjusted down by one SHIP_HOLDS worth of quantity, since
            # we would've just sold that much while there.
            noBuys = []
            for commodity in currentBuys:
                if commodity == "Fuel Ore" and otherPort.oreAmt - SHIP_HOLDS < SHIP_HOLDS:
                    noBuys.append("Fuel Ore")
                    print("Not buying Fuel Ore -- not enough demand at other port")
                    
                if commodity == "Organics" and otherPort.orgAmt - SHIP_HOLDS < SHIP_HOLDS:
                    noBuys.append("Organics")
                    print("Not buying Organics -- not enough demand at other port")
                    
                if commodity == "Equipment" and otherPort.equAmt - SHIP_HOLDS < SHIP_HOLDS:                    
                    noBuys.append("Equipment")
                    print("Not buying Equipment -- not enough demand at other port")

            for noBuyCommodity in noBuys:
                currentBuys.remove(noBuyCommodity)

            for commodity in currentBuys:
                if commodity == "Fuel Ore":
                    print("Other port is buying {0} Fuel Ore".format(otherPort.oreAmt))
                    
                if commodity == "Organics":
                    print("Other port is buying {0} Organics".format(otherPort.orgAmt))
                    
                if commodity == "Equipment":
                    print("Other port is buying {0} Equipment".format(otherPort.equAmt))
                

            # Verify there are still commodities to trade, otherwise quit.
            if not currentBuys.intersection(otherPort.buying) and not otherBuys.intersection(currentPort.buying):
                print("No more tradable commodities at these ports, in any direction. Stopping auto-trade.")
                return

            if not trade_at_port(currentPort,currentBuys):
                print("Trade exception encountered. Auto-trading stopped.")
                return
            
            #waitfor("^Command",logfile)
            flush_follow()

            # Move to other port sector
            print()
            print("===> Moving to sector {0}".format(otherSector))
            turnsLeft = turnsLeft - turnsWarp
            print("{0} turns left.".format(turnsLeft))
            if turnsLeft <= TRADE_LIMIT:
                print("Trade limit reached.  Auto-trading stopped.")
                return
            else:
                pyautogui.typewrite("m{0}\n".format(otherSector))
                waitfor("^Command",logfile)

            # Flip the trade pair
            if currentSector == sector1:
                currentSector = sector2
                currentPort = port2
                currentBuys = port2Buys
                otherSector = sector1
                otherPort = port1
                otherBuys = port1Buys
            else:
                currentSector = sector1
                currentPort = port1
                currentBuys = port1Buys
                otherSector = sector2
                otherPort = port2
                otherBuys = port2Buys                
        
    except pyautogui.FailSafeException:
        print("** ABORTED: Fail safe triggered.")
        return

# Docks at port and performs trade.
# Port - Starport of current port being docked at
# buys - Set of commodities to buy at Port
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
    elif not result and query.string.fine("Command") >= 0:
        print("Port kicked us out! Wrong cargo in holds?")
        return False
            
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
            while currentCommodity != "Equipment":
                pyautogui.typewrite("0\n")
                result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
                currentCommodity = query.group('commodity')
                print("Port offers to sell {0}".format(currentCommodity))

            if currentCommodity == "Equipment":
                print("We want to buy Equipment and port has {0} left.".format(port.equAmt))
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
            while currentCommodity != "Organics":
                pyautogui.typewrite("0\n")
                result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
                currentCommodity = query.group('commodity')
                print("Port offers to sell {0}".format(currentCommodity))

            if currentCommodity == "Organics":
                print("We want to buy Organics and port has {0} left.".format(port.orgAmt))
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
            while currentCommodity != "Fuel Ore":
                pyautogui.typewrite("0\n")
                result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile)
                currentCommodity = query.group('commodity')
                print("Port offers to sell {0}".format(currentCommodity))

            if currentCommodity == "Fuel Ore":
                print("We want to buy Fuel Ore and port has {0} left.".format(port.oreAmt))
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
# if a pattern in the "unless" list of regexes is matched, in which case it returns the
# (False,MatchObject)
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

    VERSION="1.7"
    INPUT_FILE="C:\\Temp\\tw2002a.log"
        
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


