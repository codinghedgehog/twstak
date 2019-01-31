# TradeWars Port Reporter
#
# This is a simple script that reads in saved output from a Tradewars
# session (specifically the Computer Interrogation Mode Warp Report and
# Port Report output) and generates a list of viable port pairs in the
# currently explored universe.
#

import sys
import re
import os
import datetime

# Just a container class to hold pairs of ports for easier referencing during reporting.
class TradePair:

    def __init__(self,port1,port2):

        self.port1 = port1
        self.port2 = port2

# Takes a match object from CIMPortReportRe regex to initialize.
class Starport:    
    
    def __init__(self,sector,commerceReport):

        self.sector = sector

        self.selling = set()
        self.buying = set()

        self.orgAmt = 0
        self.oreAmt = 0
        self.equAmt = 0
        
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
    global INPUT_FILENAME, OUTPUT_FILENAME
    
    selection = None
    while True:
        print()
        print("==== MAIN MENU====")
        print("i) Set input data file (Currently: {0})".format(INPUT_FILENAME))
        print("s) Save report file to (Currently: {0})".format(OUTPUT_FILENAME))
        print("r) Run report")
        print()
        print("q)  Quit")
        print()
        selection = input("Selection: ").lower()

        if selection == "i":
            INPUT_FILENAME=input("File to read: ")
            if not os.path.isfile(INPUT_FILENAME):
                print("WARNING: File {0} does not exist.".format(INPUT_FILENAME))
        elif selection == "s":
            OUTPUT_FILENAME=input("Path and filename to save report (ENTER for stdout): ")
        elif selection == "q" or selection == "Q":
            sys.exit(0)
        elif selection == "r":

            if INPUT_FILENAME is None or OUTPUT_FILENAME is None:
                print("Please specify both input and output filenames before running report!")
                continue
            
            if OUTPUT_FILENAME == "":
                trade_advisor()
            else:
                with open(OUTPUT_FILENAME,"w") as outFile:
                    trade_advisor(reportFile=outFile)
                    
            print("Done.")
            
        else:
            print("Unknown selection '{0}'".format(selection))

def trade_advisor(reportFile=None):
    # Uses Computer Interrogation Mode saved output to get list of explored sectors and port info, and advises
    # which port pairs are available.

    global INPUT_FILENAME, TRADE_PAIRS

    CIMWarpReportRe = "^ +(?P<sector>[0-9]+) +(?P<warps>[0-9 ]+)$"
    CIMPortReportRe = "^ +(?P<CIMPortSector>[0-9]+) +(?P<oreStatus>-)? +(?P<oreAmt>[0-9]+) +(?P<orePct>[0-9]+)% +(?P<orgStatus>-)? +(?P<orgAmt>[0-9]+) +(?P<orgPct>[0-9]+)% +(?P<equStatus>-)? +(?P<equAmt>[0-9]+) +(?P<equPct>[0-9]+)% $"

    warpMap = {}
    portDB = {}

    TRADE_PAIRS = []
    
    print("Loading saved CIM data...")

    inCIM = False
    with open(INPUT_FILENAME,"r") as inputFile:
        # Find first occurance of CIM prompt.
        for line in inputFile:

            if re.search("^: ENDINTERROG",line):
                inCIM = False
                
            elif re.search("^:",line):
                inCIM = True

            if inCIM:

                # See if line matches either warp report or port report output.                
                lineMatch = re.search(CIMWarpReportRe,line)
                if lineMatch:
                    warpMap[lineMatch.group('sector')] = lineMatch.group('warps').split()

                lineMatch = re.search(CIMPortReportRe,line)
                if lineMatch:
                    portDB[lineMatch.group('CIMPortSector')] = Starport(lineMatch.group('CIMPortSector'),lineMatch)                

    print("Running port analysis...")

    # For each port, look to see if there are any adjacent ports that have a viable trade flow.
    portsDone = []

    for portSector in portDB.keys():
        # Look for trade routes with adjacent ports.
        port1 = portDB[portSector]
        for adjWarp in warpMap[portSector]:
            if adjWarp in portDB.keys():

                # Skip if we've done this analysis from the other side already.
                if [adjWarp,portSector] in portsDone:
                    continue
                
                port2 = portDB[adjWarp]

                # Validate that the second port sector can warp BACK to the first sector,
                # since not all warps are bi-directional in Tradewards.
                if not portSector in warpMap[adjWarp]:
                    continue
                
                # Validate there is a viable commodity trade between the two ports.
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

    print("",file=reportFile)
    print("=== GRADE A TRADE ROUTES ===",file=reportFile)
    print("",file=reportFile)
    print_port_pair_trade_list(A_LIST,reportFile)

    print("",file=reportFile)
    print("",file=reportFile)
    print("=== GRADE B TRADE ROUTES ===",file=reportFile)
    print("",file=reportFile)
    print_port_pair_trade_list(B_LIST,reportFile)
    
    print("",file=reportFile)
    print("",file=reportFile)
    print("=== GRADE C TRADE ROUTES ===",file=reportFile)
    print("",file=reportFile)
    print_port_pair_trade_list(C_LIST,reportFile)

    print("",file=reportFile)
    print("",file=reportFile)
    print("=== GRADE D TRADE ROUTES ===",file=reportFile)
    print("",file=reportFile)
    print_port_pair_trade_list(D_LIST,reportFile)

    print("",file=reportFile)
    print("Done.")
        

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


        

if __name__ == "__main__":

    VERSION="1.7"
    INPUT_FILENAME=None
    OUTPUT_FILENAME=None

    # Holds a list of TradePairs
    TRADE_PAIRS = []

    print("***** Tradewars Port Reporter {0} *****".format(VERSION))
    print()

    do_main_menu()


