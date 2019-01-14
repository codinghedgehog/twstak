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


# Takes a match object from commerceReportRe regex to initialize.
class Starport:    
    
    def __init__(self,sector,commerceReport):

        self.sector = sector

        self.selling = set()
        self.buying = set()

        self.orgAmt = 0
        self.oreAmt = 0
        self.equAmt = 0
        
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
    global DELAY_CHAR, DELAY, TYPESPEED, FAILSAFE, FAILSAFE_DISTANCE, INPUT_FILE, TRADE_LIMIT
    
    selection = None
    while True:
        print()
        print("==== MAIN MENU====")
        print("l)  Set input log file (Currently: {0})".format(INPUT_FILE))
        print("tl) Set trade limit (Default: Stop when {0} turns left.)".format(TRADE_LIMIT))
        print("an) Auto-trade, NO haggling (CTRL-C to stop)")
        print("ay) Auto-trade, haggling (CTRL-C to stop)")
        print()
        print("b)  Begin following log file [Used for Debugging] (CTRL-C to stop)")
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
                for line in follow(INPUT_FILE):
                    print(line)
            except KeyboardInterrupt:
                print()
                print("Stopped following file")
                print()
                
        elif selection == "an":
            try:                
                auto_trade(False)
            except KeyboardInterrupt:
                print("User aborted trade routine...")
        elif selection == "ay":
            try:                
                auto_trade(True)
            except KeyboardInterrupt:
                print("User aborted trade routine...")
        else:
            print("Unknown selection '{0}'".format(selection))

def get_term_coord():
    input("Without losing focus to this window, move your mouse over the titlebar of the terminal window and press ENTER")
    mouse_x,mouse_y = pyautogui.position()
    return (mouse_x,mouse_y)

def auto_trade(negotiate=False):

    # Given two sectors, will query ports and automatically trade the highest valuable commodities
    # that can be bought/sold between the pair.
    
    global TRADE_LIMIT, commerceReportRe, logfile

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
        pyautogui.moveTo(x,y)
        pyautogui.click()

        # Check current sector and turns remaining
    
        pyautogui.typewrite("d")
        waitfor("^Command ",logfile)
        pyautogui.typewrite("i")
        result,selfInfo = return_up_to("^Command ",logfile)

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

        if not port1Buys and not port2Buys:
            print("There are no viable trade plans between these two ports!")
            return

        # Return to main prompt
        pyautogui.typewrite("q")

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

            if not trade_at_port(port1,port1Buys):
                print("Trade exception encountered. Auto-trading stopped.")
                return

            pyautogui.typewrite("d")
            waitfor("^Command",logfile)

            # Move to port2 sector
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
                print("Port depleted.  Auto-trading stopped.")
                return

            if not trade_at_port(port2,port2Buys):
                print("Turn limit reached.  Auto-trading stopped.")
                return

            pyautogui.typewrite("d")
            waitfor("^Command",logfile)

            # Move back to port1 sector
            pyautogui.typewrite("m{0}\n".format(sector1))
        
        
    except pyautogui.FailSafeException:
        print("** ABORTED: Fail safe triggered.")
        return

# Docks at port and performs trade.
def trade_at_port(port,buys):

    global logfile

    print(port)
    
    result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile,unless=["do you want to sell","Command"])
    # Sell what we have first.
    if not result and query.string.find("do you want to sell") >= 0:
        pyautogui.typewrite("\n\n")
        
        result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile,unless=["do you want to sell","Command"])
        if not result and query.string.find("do you want to sell") >= 0:
            pyautogui.typewrite("\n\n")
            
            result,query = waitfor("How many holds of (?P<commodity>.+) do you want to buy",logfile,unless=["do you want to sell","Command"])
            if not result and query.string.find("do you want to sell") >= 0:
                pyautogui.typewrite("\n\n")
            
    # If port is selling commodities.  If it is a Class 8 (BBB) port, just return, since nothing to buy.
    if buys:
        currentCommodity = query.group('commodity')
    else:
        return True
    
    # Only buy what we can sell at the other port, prioritizing equipment, organics, then ore.
    if "Equipment" in buys and port.equAmt > 0:
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
        
    elif "Organics" in buys and port.orgAmt > 0:
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
        
    elif "Fuel Ore" in buys and port.oreAmt > 0:
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

if __name__ == "__main__":

    VERSION="1.0"
    INPUT_FILE="C:\\temp\\tw2002.log"
        
    TYPESPEED=0.05
    DELAY_CHAR="`"
    DELAY=1

    FAILSAFE_DISTANCE=10
    FAILSAFE=True

    TRADE_LIMIT=40

    commerceReportRe = "Fuel Ore +(?P<oreStatus>Buying|Selling) +(?P<oreAmt>[0-9]+) .+Organics +(?P<orgStatus>Buying|Selling) +(?P<orgAmt>[0-9]+) .+Equipment +(?P<equStatus>Buying|Selling) +(?P<equAmt>[0-9]+) "

    logfile = follow(INPUT_FILE)


    print("***** STAK - Trade Tool {0} *****".format(VERSION))
    print()
    do_main_menu()


