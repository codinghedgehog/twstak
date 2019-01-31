# twstak
TradeWars 2002 Simple Telnet Auto Keyer (macro app)

Prereqs: Pyautogui

This is a Python 3 (3.6) script that uses the PyAutoGUI library to allow the defining and sending of keystrokes to a telnet window (or app, really) for the purposes of automating repetitive keystroke tasks.  This is a quick and dirty app to let TW2002 players automate paired port trading and save some finger strain.  :)

WARNING: IT IS FINICKY -- You MUST NOT move the TW2002 term window once you've defined the macro (it records the screen coordinates to click with the mouse prior to sending the keystrokes).  You also must not change focus to another window when a macro is running, otherwise the app will start sending keystrokes to whatever has focus.

NOTE: To abort the macro/app, move your mouse to the upper left most corner of the screen.  That's the failsafe.

# twstak-explorer
TradeWars 2002 Simple Telnet Auto Keyer (Explorer app)

Prereqs: Pyautogui

This is a Python 3 (3.6) script based on TWSTAK that reads scans your Explored/Unexplored sector list, then calculates which sectors to send SubSpace EtherProbes to cover the largest number of unexplored sectors.

NOTE: This requires your terminal program to log printable output to a file for the script to read.

# twstak-trader
TradeWars 2002 Simple Telnet Auto Keyer (Trader app)

Prereqs: Pyautogui, Pygtail

This is a Python 3 (3.6) script based on TWSTAK that performs paired port trading, based on the input of two sectors with viable ports in them.  It is semi-intelligent at the moment -- you can tell it stop when you have X number of turns left, and it will attempt to buy/sell the most valuable commodities first (Equipment, then Organics, finally Ore).

It also comes with a trade advisor feature, which queries known ports and finds viable port pairs for trading.

NOTE: This requires your terminal program to log printable output to a file for the script to read.

# tw_port_report
Tradewars Port Report

This is a standalone Python script that can read in a previously saved output of the Computer Interrogation Mode's Warp and Port report and generate the same trade advisor output as from the twstak-trader script.  Basically this is an offline (file-based) version of the twstak-trader's trade advisor feature.
