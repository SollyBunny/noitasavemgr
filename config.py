# Whether to use ANSII escapes for color and other stuff
ANSII = True

# Whether to ZIP files when saving, loading is unaffected
ZIP = True

# Where to store saves
SAVEDIR = "./saves"

# Where data needs to be copied from
LOADDIRS = [
	[ # One of
		"~/AppData/LocalLow/Nolla_Games_Noita/save00", # Noita Windows
		"~/.steam/steam/steamapps/compatdata/881100/pfx/drive_c/users/steamuser/AppData/LocalLow/Nolla_Games_Noita/save00", # Noita Linux Proton
		"~/.wine/drive_c/$USER/steamuser/AppData/LocalLow/Nolla_Games_Noita/save00", # Noita Linux Wine
	],
	"~/Games/NoitaEntangled/save_state", # NoitaEntangled Windows / Linux
]

# How often to create a save state (in seconds)
SAVEINTERVAL = 3 * 60 # Noita saves the game by default every 3 minutes

# Number of saves to keep if unnamed, (oldest unnamed saves are deleted)
SAVENUM = 10