#!/bin/env python3

import config
import os
import time
import threading
import datetime
import shutil
import sys
import getpass

# Util stuff

class Dict():
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

class Escaped():
	def __init__(self, strs):
		self.code = "\x1b" + "\x1b".join(strs)
	def __str__(self):
		if not config.ANSII:
			return ""
		return self.code

class Color(Escaped):
	def __init__(self, code):
		super().__init__(("[%dm" % code,))

ALTON	= Escaped(("[?1049h",))
ALTOFF	= Escaped(("[?1049l",))
CLEAR	= Escaped(("[2J", "[0H"))
CLEARR	= Escaped(("[0J",))
UPSTART	= lambda n: Escaped(("[%sF" % n,))
BLACK	= Color(30)
RED		= Color(31)
GREEN	= Color(32)
YELLOW	= Color(33)
BLUE	= Color(34)
MAGENTA	= Color(35)
CYAN	= Color(36)
WHITE	= Color(37)
DEFAULT	= Color(39)
NEWLINE	= "\n"
TAB		= "\t"

def printc(*args, **kwargs):
	print("".join(map(str, args)), **kwargs)

def inputtyped(prompt, fncvalid):
	while True:
		printc(WHITE, prompt, NEWLINE, " >>> ", CYAN, end="")
		s = input()
		o = fncvalid(s)
		if o != None:
			return o
		if len(s) == 0:
			printc(UPSTART(s.count("\n") + 2), CLEARR, end="")
		else:
			printc(UPSTART(s.count("\n") + 2), RED, "Invalid input: ", CYAN, s, CLEARR)

def inputtypedbool(s):
	s = s.lower()
	if len(s) == 0: return True
	if s[0] == "n" or s[0] == "f": return False
	if s[0] == "y" or s[0] == "t": return True

def inputtypedint(min, max):
	def f(s):
		if len(s) == 0: return
		if not s.isdigit(): return
		s = int(s)
		if s < min: return
		if s > max: return
		return s
	return f

def inputtypedpath(max):
	def f(s):
		if len(s) > max: return None
		for c in s:
			if c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 _":
				return None
		return s.replace(" ", "_")
	return f

def abspath(path):
	return os.path.abspath(os.path.expanduser(path.replace("$USER", getpass.getuser() or "user")))

def floatformat(value, decimals=2, width=6):
	value = str(round(value, 2))
	if "." not in value:
		value += "."
	value += (decimals - (len(value) - value.index(".")) + 1) * "0"
	value = value.rjust(width, " ")
	return value

def str2int(s):
	digits = "".join([char for char in s if char.isdigit()])
	return int(digits) if digits else 0

def timeago(seconds):
	intervals = (
		("year", 31536000),  # 60 * 60 * 24 * 365
		("month", 2592000),   # 60 * 60 * 24 * 30
		("week", 604800),     # 60 * 60 * 24 * 7
		("day", 86400),       # 60 * 60 * 24
		("hour", 3600),       # 60 * 60
		("minute", 60),
		("second", 1),
	)
	for name, count in intervals:
		value = seconds // count
		if value >= 1:
			if value == 1:
				return "1 %s ago" % name
			else:
				return f"%s %ss ago" % (value, name)
	return "just now"

# Main

def excepthook(exc_type, exc_value, exc_traceback):
	printc(ALTOFF, NEWLINE, CLEAR, end="", flush=True)
	if issubclass(exc_type, KeyboardInterrupt):
		return
	sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = excepthook

def deleteold(log = False):
	saves = []
	for save in os.listdir(abspath(config.SAVEDIR)):
		savedir = os.path.join(abspath(config.SAVEDIR), save)
		if not os.path.isdir(savedir): continue
		if save.count("_") != 7: continue
		save = Dict(
			time = str2int(save[:save.index("_")]),
			dir = savedir,
		)
		saves.append(save)
	saves.sort(key=lambda save: save.time, reverse=True)
	for save in saves[config.SAVENUM:]:
		if os.path.exists(save.dir):
			shutil.rmtree(save.dir)
			if log: printc(WHITE, "Deleted old save: ", CYAN, save.dir)

lock = False
def save(log = False):
	global lock
	if lock: return
	lock = True
	try:
		deleteold(log)
		start = time.time()
		savedirname = datetime.datetime.fromtimestamp(round(start)).strftime("%%s_%a_%Y_%m_%d_%H_%M_%S") % round(start)
		savedir = os.path.join(config.SAVEDIR, savedirname)
		if os.path.exists(savedir):
			return
		if log: printc(WHITE, "Starting save at ", CYAN, abspath(savedir))
		os.makedirs(abspath(savedir))
		with open(abspath(os.path.join(savedir, "paths.txt")), "w") as file:
			i = 0
			for loaddir in config.LOADDIRS:
				loaddirabs = abspath(loaddir)
				savedirpartname = "%s_%s" % (i, os.path.basename(loaddir))
				savedirpartpath = os.path.join(savedir, savedirpartname)
				savedirpartabs = abspath(savedirpartpath)
				i += 1
				if os.path.exists(loaddirabs):
					if log: printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Saving: ", CYAN, loaddir)
					file.write("%s\n%s\n\n" % (loaddir, os.path.join(savedirname, savedirpartname)))
					if os.path.isdir(loaddirabs):
						shutil.copytree(loaddirabs, savedirpartabs)
					else:
						shutil.copy(loaddirabs, savedirpartabs)
		if log: printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Finished")
	finally:
		lock = False

def load(path):
	start = time.time()
	path = abspath(path)
	printc(WHITE, "Starting load from ", CYAN, path)
	with open(os.path.join(path, "paths.txt"), "r") as file:
		files = [i.split("\n") for i in file.read().split("\n\n")]
	printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Read ", CYAN, "paths.txt")
	for file in files:
		if len(file) < 2: continue
		savedir = os.path.join(abspath(config.SAVEDIR), file[1])
		loaddir = abspath(file[0])
		if os.path.exists(loaddir):
			if os.path.isdir(loaddir):
				shutil.rmtree(loaddir)
			else:
				os.remove(loaddir)
		if os.path.exists(savedir):
			if os.path.isdir(savedir):
				shutil.copytree(savedir, loaddir)
			else:
				shutil.copy(savedir, loaddir)
		printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Loaded ", CYAN, file[0])
	printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Finished")

def promptsave(saev):
	while True:
		printc(
			NEWLINE, CLEAR, CYAN, saev.dir, NEWLINE,
			WHITE, "Pick an option, saves continue in the background every ", CYAN, config.SAVEINTERVAL, WHITE, " seconds", NEWLINE,
			CYAN, "1", WHITE, ": Exit", NEWLINE,
			CYAN, "2", WHITE, ": Delete", NEWLINE,
			CYAN, "3", WHITE, ": (Re)Name", NEWLINE,
			CYAN, "4", WHITE, ": Load", NEWLINE,
		)
		i = inputtyped("Pick an option (1-4)", inputtypedint(1, 4))
		if i == 1:
			break
		elif i == 2:
			if not inputtyped("Are you sure you want to delete this save? (Y/n)", inputtypedbool):
				continue
			shutil.rmtree(saev.dir)
			saev.dir = None
			break
		elif i == 3:
			savedirname = inputtyped("Enter new name for save (leave blank to cancel)", inputtypedpath(64))
			if len(savedirname) == 0:
				continue
			savedir = "_".join(saev.dir.split("_")[:7]) + "_" + savedirname
			os.rename(saev.dir, savedir)
			saev.dir = savedir
			saev.name = savedirname.replace("_", " ")
			break
		elif i == 4:
			print()
			save(True)
			load(saev.dir)
			input("Press enter to continue")
			break

def promptsaves(namedonly):
	saves = []
	for save in os.listdir(abspath(config.SAVEDIR)):
		savedir = os.path.join(abspath(config.SAVEDIR), save)
		if not os.path.isdir(savedir): continue
		count = save.count("_")
		if count < 7: continue
		if namedonly and count == 7: continue
		save = Dict(
			time = str2int(save[:save.index("_")]),
			dir = savedir,
			name = " ".join(save.split("_")[7:]) if count > 7 else None,
		)
		saves.append(save)
	if len(saves) == 0:
		printc(NEWLINE, WHITE, "No %ssaves found, press enter to continue" % ("named " if namedonly else ""))
		input()
		return
	saves.sort(key = lambda save: save.time)
	offset = 0
	now = round(time.time())
	while True:
		printc(CLEAR, end="")
		i = 3
		for save in saves[offset:]:
			i += 1
			printc(
				CYAN, str(i).rjust(3), WHITE, ": ", CYAN, "%s " % save.name if save.name else "", WHITE, datetime.datetime.fromtimestamp(save.time).strftime("%A %Y/%m/%d %H:%M.%S"), " (", timeago(now - save.time), ")"
			)

		printc(
			WHITE, "Pick an option, saves continue in the background every ", CYAN, config.SAVEINTERVAL, WHITE, " seconds", NEWLINE,
			CYAN, "1", WHITE, ": Exit", NEWLINE,
			CYAN, "2", WHITE, ": Scroll Up", NEWLINE,
			CYAN, "3", WHITE, ": Scroll Down", NEWLINE,
		)

		i = inputtyped("Pick an option (1-%s)" % i, inputtypedint(1, i))

		if i == 1:
			break
		elif i == 2:
			offset -= 3
			offset = max(0, offset)
		elif i == 3:
			offset += 3
		else:
			promptsave(saves[offset + i - 4])
			saves = list(filter(lambda save: save.dir, saves))

def prompt():
	printc(
		CLEAR, WHITE, "Pick an option, saves continue in the background every ", CYAN, config.SAVEINTERVAL, WHITE, " seconds", NEWLINE,
		CYAN, "1", WHITE, ": Exit", NEWLINE,
		CYAN, "2", WHITE, ": Manual save", NEWLINE,
		CYAN, "3", WHITE, ": List all saves", NEWLINE,
		CYAN, "4", WHITE, ": List all named saves", NEWLINE
	)

	i = inputtyped("Pick an option (1-4)", inputtypedint(1, 4))

	if i == 1:
		return False
	elif i == 2:
		print()
		save(True)
		input("Press enter to continue")
	elif i == 3:
		promptsaves(False)
	elif i == 4:
		promptsaves(True)

	print()
	return True

printc(
	ALTON, CLEAR,
	WHITE, "Config can be found in ", CYAN, "config.py", WHITE, " in the working directory", NEWLINE, NEWLINE,
	WHITE, "Save Directory:   ", CYAN, config.SAVEDIR, NEWLINE,
	WHITE, "Load Directories: ", CYAN, "\n                  ".join(config.LOADDIRS), NEWLINE, NEWLINE,
	WHITE, "Save Interval:    ", CYAN, config.SAVEINTERVAL, WHITE, " seconds", NEWLINE,
	WHITE, "Max Saves:        ", CYAN, config.SAVENUM, NEWLINE,
)

inputtyped("Is this config okay, type no to exit (Y/n)", inputtypedbool)

running = True

def autosave(*args):
	global running
	while running:
		slept = 0
		while slept < config.SAVEINTERVAL and running:
			time.sleep(1)
			slept += 1
		save(False)

threading.Thread(target = autosave).start()

printc(NEWLINE, CLEAR, end="")

while prompt():
	pass
running = False

printc(ALTOFF, end="")

