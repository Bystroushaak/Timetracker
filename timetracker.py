#!/usr/bin/env python
# -*- coding: utf-8 -*-
__name    = "timetracker"
__version = "1.0.0"
__date    = "09.12.2012"
__author  = "Bystroushaak"
__email   = "bystrousak@kitakitsune.org"
# 
# Interpreter version: python 2.7
# This work is licensed under a Creative Commons 3.0 
# Unported License (http://creativecommons.org/licenses/by/3.0/).
# Created in Sublime text 2 editor.
#
# Notes:
    # 
#= Imports =====================================================================
import os
import sys
import time
import os.path
import argparse

import pyinotify



#= Variables ===================================================================
CONF_DIR     = os.path.expanduser("~/.timetracker")
WATCHLIST_FN = CONF_DIR + "/" + "watchlist.txt"
WATCHLOG_FN  = CONF_DIR + "/" + "watchlog.txt"
MIN_TIME_DIFF = 5 * 60 # 5m



#= Functions & objects =========================================================
def write(s, out=sys.stdout):
	out.write(str(s))
	out.flush()
def writeln(s, out=sys.stdout):
	write(s + "\n")
def version():
	return __name + " v" + __version + " (" + __date + ") by " + __author + " (" + __email + ")"


def readFile(fn):
	"Just read file and return it as string."

	fh = open(fn, "rt")
	data = fh.read()
	fh.close()

	return data

def readWatchlist(fn):
	"Read file and return it as unsorted unique list. Filter blank lines."

	return list(set(filter(lambda x: x.strip() != "", readFile(fn).splitlines())))


def addToFile(fn, line):
	"Append line to the file identified with fn."

	fh = open(fn, "a")
	fh.write(line.strip() + "\n")
	fh.close()


def saveList(fn, data):
	"Save list to the file as string."

	fh = open(fn, "wt")
	fh.write("\n".join(data) + "\n")
	fh.close()


def printWatchlist(wl):
	"Print numbered list, if blank, show let user know and exit."

	if len(wl) <= 0:
		writeln("There is nothing on watchlist.")
		sys.exit(0)

	cnt = 0
	for l in wl:
		writeln(str(cnt) + "\t" + l)
		cnt += 1


def analyzeLogFiles(watchlist, loglist):
	"Analyze watchlist and loglist and return stats for each project listed in watchlist."

	data = {}
	for project in watchlist:
		data[project] = 0
		data[project + "_lt"] = 0

	# read saved data from logfile
	for line in loglist:
		# skip regular log records and blank lines
		if not line.startswith("saved") or line.strip() == "":
			continue

		# get saved results
		line  = line.split(" ")
		saved = int(line[1])
		last  = int(line[2])

		# join rest of the path back
		line = " ".join(line[3:]).strip()

		data[line + "_lt"] = last
		data[line] = saved

	# process logfile for file access
	for project in filter(lambda line: not line.startswith("saved"), watchlist):
		for line in loglist:
			# skip saved records and blank lines
			if line.startswith("saved") or line.strip() == "":
				continue

			# parse date
			date = int(line[:10])
			line = line[11:]

			# count only records which diff more than MIN_TIME_DIFF
			if line.startswith(project) and abs(date - data[project + "_lt"]) > MIN_TIME_DIFF:
				data[project] += 1
				data[project + "_lt"] = date

	return data


class EventHandler(pyinotify.ProcessEvent):
	"Event based system. Bleh."

	def monitorEvent(self, event):
		writeln(event.maskname + " " + event.pathname)
		addToFile(WATCHLOG_FN, str(int(time.time())) + " " + event.pathname)

	def process_IN_CREATE(self, event):
		self.monitorEvent(event)
	def process_IN_DELETE(self, event):
		self.monitorEvent(event)
	def process_IN_MODIFY(self, event):
		self.monitorEvent(event)



#= Main program ================================================================
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument(
		"-d",
		"--daemon",
		action  = "store_true",
		default = False,
		help    = "Run as daemon, monitor filesystem changes."
	)
	parser.add_argument(
		"-l",
		"--list",
		action  = "store_true",
		default = False,
		help    = "List all watched projects."
	)
	parser.add_argument(
		"-s",
		"--stats",
		action  = "store_true",
		default = False,
		help    = "Show stats for watched projects."
	)
	parser.add_argument(
		"-a",
		"--add",
		metavar = "DIR NAME",
		action  = "store",
		default = "",
		type    = str,
		nargs   = "?",
		help    = "Add new project to the watchlist."
	)
	parser.add_argument(
		"-r",
		"--remove",
		metavar = "ID",
		action  = "store",
		type    = int,
		default = -1,
		help    = "Remove project identified by ID. See --list for list of all IDs."
	)
	parser.add_argument(
		"-v",
		"--version",
		action  = "store_true",
		default = False,
		help    = "Show version."
	)
	args = parser.parse_args()

	# make sure all files exists
	if not os.path.exists(CONF_DIR):
		os.makedirs(CONF_DIR)
	if not os.path.exists(WATCHLIST_FN):
		saveList(WATCHLIST_FN, [])
	if not os.path.exists(WATCHLOG_FN):
		saveList(WATCHLOG_FN, [])
	wl = readWatchlist(WATCHLIST_FN)


	# react to user wishes
	if args.version:
		writeln(version())
		sys.exit(0)

	elif args.list:
		printWatchlist(wl)

	elif args.add != "":
		# get absolute path of file user wants add
		pp = os.path.abspath(os.path.expanduser(args.add.strip()))

		# check if file exists
		if not os.path.exists(pp):
			writeln("Selected path '" + pp + "' doesn't exist!", sys.stderr)
			sys.exit(2)

		addToFile(WATCHLIST_FN, pp)

	elif args.remove >= 0 and args.remove < len(wl):
		del wl[args.remove]

		saveList(WATCHLIST_FN, wl)

		printWatchlist(wl)

	elif args.stats:
		# analyze logs
		data = analyzeLogFiles(wl, readFile(WATCHLOG_FN).splitlines())
		
		# print results and save it 
		new_ll = []
		for project in filter(lambda x: not x.endswith("_lt"), data.keys()):
			writeln("Aprox. " + str(data[project] * MIN_TIME_DIFF) + "s\t" + project)

			# memorize results for next time
			new_ll.append("saved " + str(data[project]) + " " + str(data[project + "_lt"]) + " " + project)

		# save results - this saves a lot of time and some diskspace
		saveList(WATCHLOG_FN, new_ll)

	elif args.daemon:
		# well, run at background and log access to the projects
		wm = pyinotify.WatchManager()
		notifier = pyinotify.Notifier(wm, EventHandler())

		for w in wl:
			wm.add_watch(w, pyinotify.ALL_EVENTS, rec=True)

		notifier.loop()
