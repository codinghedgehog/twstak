# twstak
TradeWars 2002 Simple Telnet Auto Keyer (macro app)

This is a Python 3 (3.6) script that uses the PyAutoGUI library to allow the defining and sending of keystrokes to a telnet window (or app, really) for the purposes of automating repetitive keystroke tasks.  This is a quick and dirty app to let TW2002 players automate paired port trading and save some finger strain.  :)

WARNING: IT IS FINICKY -- You MUST NOT move the TW2002 term window once you've defined the macro (it records the screen coordinates to click with the mouse prior to sending the keystrokes).  You also must not change focus to another window when a macro is running, otherwise the app will start sending keystrokes to whatever has focus.

NOTE: To abort the macro/app, move your mouse to the upper left most corner of the screen.  That's the failsafe.
