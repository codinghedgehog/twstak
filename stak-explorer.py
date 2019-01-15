# Simple TradeWars2002 Automatic Keypresser (STAK) - Explorer Utility
#
# Using the Known/Unknown Universe feature to determine the most
# efficient use of SubSpace Ether probes.  It basically finds the
# max number of unexplored sectors (from your current sector) a
# probe will pass through when sent to a given unknown sector.
#
# This requires the user to save the terminal output to a log file for
# real-time parsing.
#
# Uses: pyautogui
#

import sys
import re
import os
import pyautogui
from time import sleep

VERSION="1.1"
INPUT_FILE="C:\\Temp\\tw2002a.log"
    
TYPESPEED=0.05
DELAY_CHAR="`"
DELAY=1

FAILSAFE_DISTANCE=10
FAILSAFE=True

# exploreDB keys off of individual destination sectors and the value is the set of
# unexplored sectors passed through if a probe is sent to that destination sector.
exploreDB = {}

tallyDB = {}

def do_main_menu():
    global DELAY_CHAR, DELAY, TYPESPEED, FAILSAFE, FAILSAFE_DISTANCE, INPUT_FILE, exploreDB
    
    selection = None
    while True:
        print()
        print("==== MAIN MENU====")
        print("l) Set input log file (Currently: {0})".format(INPUT_FILE))
        print("b) Begin following log file [Used for Debugging] (CTRL-C to stop)")
        print("c) Collect probe path data (CTRL-C to stop)")
        print("d) Dump/Show current probe path data")
        print("i) Calculate intelligent probe pattern")
        print()
        print("dc) Set macro delay char (Currently: {0})".format(DELAY_CHAR))
        print("dv) Set macro delay char value (Currently: {0} seconds)".format(DELAY))
        print("td) Set inter-character typing delay (Currently {0} seconds)".format(TYPESPEED))
        print("f) Toggle FAILSAFE (aborts macro on mouse movement): Currently {0}".format(FAILSAFE))
        print()
        print("q) Quit")
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
        elif selection == "d":
            print()
            print(exploreDB)
            print()
            print(tallyDB)
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
                
        elif selection == "c":
            try:
                print("Collecting probe path data...")
                analyze_probe_destinations()
            except KeyboardInterrupt:
                print("Aborted command...")                
        elif selection == "i":
            create_intelligent_probe_plan()
        else:
            print("Unknown selection '{0}'".format(selection))

def get_term_coord():
    input("Without losing focus to this window, move your mouse over the titlebar of the terminal window and press ENTER")
    mouse_x,mouse_y = pyautogui.position()
    return (mouse_x,mouse_y)

def create_intelligent_probe_plan():
    # Rather than just a straight up tally of number of unexplored sectors visited when sent to a given
    # destination, this starts from exploring the destination with the highest number of pass-through
    # unexplored sectors, then "remembers" those pass-through sectors so that subsequent encounters (i.e.
    # when going to another destination) won't count them as unexplored.  This thus creates a sequence of
    # destination sectors that will explore the max number of unique remaining unexplored sectors.

    global tallyDB, exploreDB
    
    buildTally()
    
    # Find the destination sectors passing through the greatest number of unexplored sectors.
    # Choose one as the first sector to explore in the intelligent plan.
    sector_count_list = list(tallyDB.keys())
    sector_count_list.sort()
    sector_count_list.reverse()

    starting_sector = tallyDB[sector_count_list[0]][0]

    # Now rebuild tally data, not counting previously explored new sectors, starting from the
    # destination sector with the highest number of unexplored sectors passed through.
    
    explored_sectors = set()
    explored_sectors = explored_sectors.union(exploreDB[starting_sector])

    tallyDB2 = {}
    tallyDB2[len(exploreDB[starting_sector])] = [starting_sector]

    for sector_count in sector_count_list:

        for sector in tallyDB[sector_count]:

            if sector == starting_sector:
                continue

            new_sector_count = len(exploreDB[sector] - explored_sectors)
            
            if new_sector_count in tallyDB2.keys():
                tallyDB2[new_sector_count].append(sector)
            else:
                tallyDB2[new_sector_count] = [sector]

            explored_sectors = explored_sectors.union(exploreDB[sector])

    tallyDB = tallyDB2
    reportTally()

def analyze_probe_destinations():
    global INPUT_FILE, exploreDB

    exploreDB = {}

    print()
    print("Be sure your terminal program is logging printable output to {0} before continuing.".format(INPUT_FILE))
    print()
    #yorn = input("Proceed? (y/n) ").lower()
    #if yorn != "y":
    #    return
    
    x,y = get_term_coord()

    yorn = input("Are you already at main command prompt? y/n ").lower()
    if yorn != "y":
        print("Please be at the main command (NOT Computer) prompt before mapping.")
        return

    try:            
        pyautogui.moveTo(x,y)
        pyautogui.click()

        logfile = follow(INPUT_FILE)

        # Active computer
        pyautogui.typewrite("c")
        waitfor("^Computer command",logfile)

        # <K> Your Known Universe
        pyautogui.typewrite("k")
        waitfor("E/U",logfile)

        # (U)nexplored sectors
        pyautogui.typewrite("u")
        waitfor("You have NOT explored the following sectors:",logfile)

        # Grab output of unexplored sectors.
        sector_output = return_up_to("^Computer command",logfile)
        
        # For each unexplored sector, see how many other unexplored sectors are passed through
        # on the way there from the current sector.
        unexplored_sector_list = sector_output.split()

        for sector in unexplored_sector_list:
            if not re.match("[0-9]+",sector):
                continue
            
            pyautogui.typewrite("f")
            waitfor("^What is the starting sector",logfile)

            # Accept default (current sector)
            pyautogui.typewrite("\n")

            waitfor("^What is the destination sector?",logfile)
            pyautogui.typewrite(sector + '\n')

            waitCheck = waitfor("^The shortest path",logfile,unless=["^Clear Avoids"])
            if waitCheck is True:
                probe_path = return_up_to("^Computer command",logfile)
            else:
                # We tried going to a sector unreachable due to avoids, so it asked us
                # if we wanted to clear avoids.  Say NO, and go to next sector to test.
                pyautogui.typewrite("n")
                continue

            if sector not in exploreDB:
                exploreDB[sector] = set()
                
            for unexploredSector in re.findall("\(([0-9]+)\)",probe_path):                
                exploreDB[sector].add(unexploredSector)        

        buildTally()
        reportTally()
        
    except pyautogui.FailSafeException:
        print("** ABORTED: Fail safe triggered.")
        return

def buildTally():
    global exploreDB, tallyDB

    tallyDB = {}

    for data in exploreDB.items():
        sector = data[0]
        unexplored_count = len(data[1])

        if not unexplored_count in tallyDB.keys():
            tallyDB[unexplored_count] = [sector]
        else:
            tallyDB[unexplored_count].append(sector)

def reportTally():
    global tallyDB
    
    # Find the destination sectors passing through the greatest number of unexplored sectors.
    sector_count_list = list(tallyDB.keys())
    sector_count_list.sort()
    sector_count_list.reverse()

    print("Number of unexplored sectors revealed by destination sector:")

    for sector_count in sector_count_list:
        print("{0} new sectors explored if you send to {1}".format(sector_count,tallyDB[sector_count]))


def return_up_to(regex,logfile):
    output = ""
    for line in logfile:
        #print("Checking {0} for {1}".format(line, regex))
        #print(re.search(regex,line))
        if re.search(regex,line):
            return output
        else:
            output = output + line

# Consumes lines from logfile unti regex matches and returns True, or
# if a pattern in the "unless" list of regexes is matched, in which case it returns the
# index number of the matched pattern in the "unless" list variable.
def waitfor(regex,logfile,unless=[]):
    for line in logfile:
        #print("Checking {0} for {1}".format(line, regex))
        #print(re.search(regex,line))
        if re.search(regex,line):
            return True

        # Check exceptions
        unlessIndex = 0
        for unlessPattern in unless:
            unlessIndex = unlessIndex + 1
            if re.search(unlessPattern,line):
                return False

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

    print("***** STAK - Explorer Tool {0} *****".format(VERSION))
    print()
    do_main_menu()


