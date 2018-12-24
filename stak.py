# Simple TradeWars2002 Automatic Keypresser (STAK)
#
# Allows user to define and playback keypresses.
# This is mostly to faciliate TradeWars 2002 port trading
# and other simple repetitive tasks.
#
# Uses: pyautogui
#
# Other Notes: I considered using some platform specific libraries
# like pywin32 and/or pywinauto to better handle Windows manipulation
# like using the actual Windows handle to give/check focus when
# running macros, but decided to stick with using only the
# cross-compatible pyautogui library for now, so it should work on
# any platform that can install Python 3 and pyautogui.

import sys
import os
import pyautogui
from time import sleep

VERSION="1.1"
    
macros = {}
macro_list = []
TYPESPEED=0.05
DELAY_CHAR="`"
DELAY=1

FAILSAFE_DISTANCE=10
FAILSAFE=True

def do_main_menu():
    global DELAY_CHAR, DELAY, TYPESPEED, FAILSAFE, FAILSAFE_DISTANCE
    
    selection = None
    while True:
        print()
        print("==== MAIN MENU====")
        print("l) List macros")
        print("c) Create macro")
        print("r) Run macro")
        print("m) Run macro multiple times")
        print("d) Delete macro")
        print()
        print("dc) Set macro delay char (Currently: {0})".format(DELAY_CHAR))
        print("dv) Set macro delay char value (Currently: {0} seconds)".format(DELAY))
        print("td) Set inter-character typing delay (Currently {0} seconds)".format(TYPESPEED))
        print()
        print("f) Toggle FAILSAFE (aborts macro on mouse movement): Currently {0}".format(FAILSAFE))
        print()
        print("q) Quit")
        print()
        selection = input("Selection: ").lower()

        if selection == "c":
            create_macro()
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
        elif len(macro_list) == 0:
            print("No macros defined.")
        elif selection == "l":
            list_macros()
        elif selection == "c":
            create_macro()
        elif selection == "r":
            run_macro()
        elif selection == "m":
            times = input("Times to run macro: ")
            run_macro(repeat=int(times))
        elif selection == "d":
            delete_macro()
        else:
            print("Unknown selection '{0}'".format(selection))

def list_macros():
    
    print()
    print("---- Macros ----")
    print()
    i = 1
    for macro in macro_list:
        print("{0}. {1} = {2}".format(str(i),macro,macros[macro]['seq']))
        i = i + 1
        
    print()

def create_macro():

    print()
    print("---- Creating New Macro ----")
    print()
    input("Step 1: While keeping this window active, move the mouse to the target window to run the macro on, and press ENTER.")    
    mouse_x, mouse_y = pyautogui.position()
    print("Clicked at {0},{1}".format(mouse_x, mouse_y))
    print()
    macro_seq = input("Step 2: Enter the key sequence you want to transmit to the target screen (may use \\n for ENTER): ")
    print()
    macro_name = input("Enter name of macro: ")
    macros[macro_name] = {'x': mouse_x, 'y': mouse_y, 'seq': macro_seq}
    macro_list.append(macro_name)
    print("Macro {0} defined.".format(macro_name))      

def run_macro(repeat=1):

    print()
    print("---- Run Macro ({0} times) ----".format(repeat))
    print()
    i = 1
    mapping={}
    for macro in macro_list:
        print("{0}. {1}".format(str(i),macro))
        mapping[str(i)] = macros[macro]
        i = i + 1

    print()
    print("q. Quit")
    print()
    selection = input("Select macro to run: ")

    if selection == "q":
        return

    if not selection in mapping:
        print("Invalid selection.")
        return
    
    selected_macro =  mapping[selection]
    
    print()

    try:
        pyautogui.moveTo(selected_macro['x'],selected_macro['y'])
        pyautogui.click()

        i=0
        while i < repeat:
            
            #pyautogui.typewrite(selected_macro['seq'].encode('utf-8').decode('unicode_escape'), interval=TYPESPEED)
            seq_list = selected_macro['seq'].split(DELAY_CHAR)
            
            for index in range(len(seq_list)):
                
                # FAILSAFE: Make sure mouse hasn't moved a significant amount (and potentially lost focus to target window),
                # when sending macro sequences.
                mouse_x, mouse_y = pyautogui.position()
                diffx = abs(mouse_x - selected_macro['x'])
                diffy = abs(mouse_y - selected_macro['y'])
                if FAILSAFE and ((diffx > FAILSAFE_DISTANCE) or (diffy > FAILSAFE_DISTANCE)):
                    print("*** FAILSAFE TRIGGERED (mouse moved off x,y): Aborting macro")
                    return
                
                pyautogui.typewrite(seq_list[index].encode('utf-8').decode('unicode_escape'),interval=TYPESPEED)
                #for key in seq_list[index].encode('utf-8').decode('unicode_escape'):
                #   pyautogui.press(key)

                # Don't delay after last subsequence is sent
                if index < len(seq_list) - 1:                
                    sleep(DELAY)

            i = i + 1

            print("Times run: {0} (moving mouse to upper left screen corner aborts)".format(i))
    except pyautogui.FailSafeException:
        print("*** FAILSAFE TRIGGERED (screen corner hit): Aborting macro")
        return


        
def delete_macro():
    
    print()
    print("---- DELETE Macro ----")
    print()
    i = 1
    mapping={}
    for macro in macro_list:
        print("{0}. {1}".format(str(i),macro))
        mapping[str(i)] = macro
        i = i + 1
        
    print()
    print("q. Quit")
    print()
    
    selection = input("Select macro to DELETE: ")

    if selection == "q":
        return

    if not selection in mapping:
        print("Invalid selection.")
        return

    del macros[mapping[selection]]
    macro_list.remove(mapping[selection])
    
    print("Deleted macro {0}".format(mapping[selection]))
    

if __name__ == "__main__":

    print("***** Simple Tradewars Auto Keyer {0} *****".format(VERSION))
    print()
    do_main_menu()


