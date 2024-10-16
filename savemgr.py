#!/bin/env python3

import os
import time
import threading
import datetime
import shutil
import sys
import getpass
import zipfile

import config

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
		("year",   60 * 60 * 24 * 365),
		("month",  60 * 60 * 24 * 30),
		("week",   60 * 60 * 24 * 7),
		("day",    60 * 60 * 24),
		("hour",   60 * 60),
		("minute", 60),
		("second", 1),
	)
	for name, count in intervals:
		value = seconds // count
		if value >= 1:
			if value == 1:
				return "1 %s ago" % name
			else:
				return "%s %ss ago" % (value, name)
	return "just now"

def isiterable(obj):
	return not isinstance(obj, str) and hasattr(obj, "__iter__")

def flattenlist(nestedlist):
	flattened = []
	for item in nestedlist:
		if isiterable(item):
			flattened.extend(item)
		else:
			flattened.append(item)
	return flattened

def zipfileread(zipfilepath, outpath):
	with zipfile.ZipFile(zipfilepath, "r") as zipf:
		zipf.extractall(outpath)

# Main

running = True
def excepthook(exc_type, exc_value, exc_traceback):
	global running
	running = False
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
		# delete old saves
		deleteold(log)
		# figure out path to save
		start = time.time()
		savedirname = datetime.datetime.fromtimestamp(round(start)).strftime("%%s_%a_%Y_%m_%d_%H_%M_%S") % round(start)
		if config.ZIP:
			savedir = os.path.join(config.SAVEDIR, savedirname) + ".zip"
			if os.path.exists(savedir):
				return
		else:
			savedir = os.path.join(config.SAVEDIR, savedirname)
			if os.path.exists(savedir):
				return
			os.makedirs(abspath(savedir))
		if log: printc(WHITE, "Starting save at ", CYAN, abspath(savedir))
		outpaths = ""
		outfiles = []
		i = -1
		for loaddirlist in config.LOADDIRS:
			i += 1
			# find which loaddir in loaddirlist is valid
			if not isiterable(loaddirlist):
				loaddirlist = [loaddirlist]
			if len(loaddirlist) == 0:
				continue
			for loaddir in loaddirlist:
				loaddirabs = abspath(loaddir)
				if os.path.exists(loaddirabs):
					break
				loaddir = None
			if not loaddir:
				continue
			savedirpartname = "%s_%s" % (i, os.path.basename(loaddir))
			# add to paths.txt
			outpaths += "\n".join((savedirpartname, *loaddirlist)) + "\n\n"
			# copy files
			outfiles.append([savedirpartname, loaddirabs])
		if log: printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Saving: ", CYAN, "paths.txt")
		# start writing
		if config.ZIP:
			with zipfile.ZipFile(savedir, "w", zipfile.ZIP_DEFLATED) as zipf:
				zipf.writestr("paths.txt", outpaths)
				for file in outfiles:
					if log: printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Saving: ", CYAN, file[0])
					for root, dirs, files in os.walk(file[1]):
						for f in files:
							f = os.path.join(root, f)
							o = os.path.join(file[0], os.path.relpath(
								os.path.join(root, f), file[1]
							))
							zipf.write(f, o)
		else:
			with open(abspath(os.path.join(savedir, "paths.txt")), "w") as file:
				file.write(outpaths)
			for file in outfiles:
				if log: printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Saving: ", CYAN, file[0])
				file[0] = abspath(os.path.join(savedir, file[0]))
				if os.path.isdir(file[1]):
					shutil.copytree(file[1], file[0])
				else:
					shutil.copy(file[1], file[0])
		if log: printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Finished")
	finally:
		lock = False

def load(path):
	global lock
	if lock: return
	lock = True
	zipf = None
	try:
		start = time.time()
		path = abspath(path)
		printc(WHITE, "Starting load from ", CYAN, path)
		if os.path.isdir(path):
			with open(os.path.join(path, "paths.txt"), "r") as file:
				files = [i.split("\n") for i in file.read().split("\n\n")]
		else:
			zipf = zipfile.ZipFile(path, "r")
			files = [i.split("\n") for i in zipf.read("paths.txt").decode().split("\n\n")]
		printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Read ", CYAN, "paths.txt")
		for file in files:
			if len(file) < 2: continue
			savedir = os.path.join(path, file[0])
			for loaddir in file[1:]:
				if len(loaddir) > 0:
					loaddirabs = abspath(loaddir)
					if os.path.exists(os.path.dirname(loaddirabs)):
						break
				loaddir = None
			if loaddir == None: continue
			printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Loading ", CYAN, loaddir)
			if os.path.exists(loaddirabs):
				if os.path.isdir(loaddirabs):
					shutil.rmtree(loaddirabs)
				else:
					os.remove(loaddirabs)
			if os.path.isdir(path):
				if os.path.exists(savedir):
					if os.path.isdir(savedir):
						shutil.copytree(savedir, loaddirabs)
					else:
						shutil.copy(savedir, loaddirabs)
			else:
				for info in zipf.infolist():
					if info.filename.startswith(file[0]):
						o = os.path.join(loaddirabs, info.filename[info.filename.index("/") + 1:])
						odir = os.path.dirname(o)
						if not os.path.exists(odir):
							os.makedirs(odir)
						if info.is_dir():
							continue
						with open(o, "wb") as ofile:
							ofile.write(zipf.read(info.filename))
		printc(TAB, CYAN, floatformat(time.time() - start), WHITE, ": Finished")
	finally:
		lock = False
		if zipf:
			zipf.close()

def promptsave(saev):
	while True:
		printc(
			NEWLINE, CLEAR, CYAN, saev.dir, NEWLINE,
			WHITE, "Pick an option, saves continue in the background every ", CYAN, config.SAVEINTERVAL, WHITE, " seconds", NEWLINE,
			CYAN, "1", WHITE, ": Exit", NEWLINE,
			CYAN, "2", WHITE, ": Delete", NEWLINE,
			CYAN, "3", WHITE, ": ", "Rename" if saev.name else "Name", NEWLINE,
			CYAN, "4", WHITE, ": Load", NEWLINE,
			CYAN, "5", WHITE, ": ", "Unzip" if saev.zip else "Zip", NEWLINE,
		)
		i = inputtyped("Pick an option (1-5)", inputtypedint(1, 5))
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
			savedir = "_".join(saev.dir.split("_")[:8]) + "_" + savedirname
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
		elif i == 5:
			if saev.zip:
				outdir = saev.dir
				if "." in outdir:
					outdir = outdir[:outdir.rindex(".")]
				if os.path.exists(outdir):
					printc(WHITE, "Folder already exists, press enter to continue")
					input()
					continue
				os.makedirs(outdir)
				with zipfile.ZipFile(saev.dir, "r") as zipf:
					zipf.extractall(outdir)
				os.remove(saev.dir)
				saev.dir = outdir
				saev.zip = False
			else:
				outdir = saev.dir
				if os.path.exists(outdir + ".zip"):
					printc(WHITE, "File already exists, press enter to continue")
					input()
					continue
				shutil.make_archive(outdir, "zip", saev.dir)
				shutil.rmtree(saev.dir)
				saev.dir = outdir + ".zip"
				saev.zip = True
			break

def promptsaves(namedonly):
	saves = []
	for save in os.listdir(abspath(config.SAVEDIR)):
		savedir = os.path.join(abspath(config.SAVEDIR), save)
		count = save.count("_")
		if count < 7: continue
		if namedonly and count == 7: continue
		if count > 7:
			name = " ".join(save.split("_")[8:])
			if "." in name:
				name = name[:name.rindex(".")]
		else:
			name = None
		save = Dict(
			time = str2int(save[:save.index("_")]),
			dir = savedir,
			name = name,
			zip = not os.path.isdir(savedir),
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
				CYAN, str(i).rjust(3), WHITE, ": ", CYAN, "%s " % save.name if save.name else "", WHITE, datetime.datetime.fromtimestamp(save.time).strftime("%A %Y/%m/%d %H:%M.%S"), " (", timeago(now - save.time), ")", " (zipped)" if save.zip else "",
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
	WHITE, "Load Directories: ", CYAN, "\n                  ".join(flattenlist(config.LOADDIRS)), NEWLINE, NEWLINE,
	WHITE, "Save Interval:    ", CYAN, config.SAVEINTERVAL, WHITE, " seconds", NEWLINE,
	WHITE, "Max Saves:        ", CYAN, config.SAVENUM, NEWLINE,
	WHITE, "Save with zip:    ", CYAN, config.ZIP, NEWLINE,
)

inputtyped("Is this config okay, type no to exit (Y/n)", inputtypedbool)

def autosave(*args):
	global running
	while True:
		slept = 0
		while slept < config.SAVEINTERVAL and running:
			time.sleep(1)
			slept += 1
		if not running: break
		save(False)

threading.Thread(target = autosave).start()

printc(NEWLINE, CLEAR, end="")

while prompt():
	pass
running = False

printc(ALTOFF, end="")

