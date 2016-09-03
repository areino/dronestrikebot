#!/usr/bin/python

import twitter
import string
import os.path
import time
import sys
from time import gmtime, strftime

# Initialization variables
CONSUMER_KEY        = ''
CONSUMER_SECRET     = ''
ACCESS_TOKEN_KEY    = ''
ACCESS_TOKEN_SECRET = ''
FILE_LASTID         = 'lastid.txt'
FILE_LASTDM         = 'lastdm.txt'
FILE_LASTSTRIKES    = 'laststrikes.txt'
FILE_DEBUG          = 'debug.log'
MINIMUM_DELAY       = 360 # Seconds to wait for same user to order new strike
LOOP_DELAY          = 90 # Seconds to wait after each loop
FETCH_FOLLOWERS     = 10 # Update follower list every n loops
COMMANDER           = '' # Lowercase screen name (without @) of user who can send commands by DM


# Connecting to Twitter API
api = twitter.Api(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET,
                  access_token_key=ACCESS_TOKEN_KEY, access_token_secret=ACCESS_TOKEN_SECRET)
api.sleep_on_rate_limit = True


# Write debug log
def writeLog(content):
	currenttime = strftime("%Y-%m-%d %H:%M:%S", gmtime())
	#with open(FILE_DEBUG, "a") as f:
	#	f.write(currenttime + " - " + content + "\n")
	print currenttime + " - " + content



# Retrieve last DM ID fetched from local file
def getLastDM():
        if os.path.exists(FILE_LASTDM):
                with open(FILE_LASTDM, "r") as f:
                        l = f.readline()
                        return(int(l))
        else:
                writeLog("No last DM ID recorded.")
                return(0)

# Write last mention ID fetched to local file
def setLastDM(lastid):
        with open(FILE_LASTDM, "w") as f:
                f.write(str(lastid))


# Command and control
def processCC():
	newlastdm = 0
	lastdm = getLastDM()
	#writeLog("C&C - Last DM processed was " + str(lastdm))
	for dm in api.GetDirectMessages(since_id=lastdm):
		t = dm.text.strip().lower()
		writeLog("C&C - " + t + " [" + str(dm.sender_screen_name) + "]")
		if newlastdm<dm.id:
			newlastdm = dm.id
			setLastDM(newlastdm)
			if dm.sender_screen_name.lower() == COMMANDER:
				# Commands
				if t.find("ping") > -1:
					writeLog("C&C - Ping received from " + dm.sender_screen_name)
					api.PostDirectMessage("Alive!", user_id=dm.sender_id)
				if t.find("shutdown") > -1:
					writeLog("C&C - Shutdown received from " + dm.sender_screen_name)
					api.PostDirectMessage("Shutting down!", user_id=dm.sender_id)
					exit(1)


# Retrieve last mention ID fetched from local file
def getLastID():
	if os.path.exists(FILE_LASTID):
		with open(FILE_LASTID, "r") as f:
			l = f.readline()
			return(int(l))
	else:
		writeLog("No last ID recorded.")
		return(0)

# Write last mention ID fetched to local file
def setLastID(lastid):
	with open(FILE_LASTID, "w") as f:
		f.write(str(lastid))

# Check if user is follower of self
def isFollower(userid):
	global followers
	found = False
	for u in followers:
		if u.id == userid:
			found = True
			break
	return found


# Retrieve last strike by user from local file and return number of seconds until now
def getSecondsLastStrike(userid):
	ret = 0
	if os.path.exists(FILE_LASTSTRIKES):
		with open(FILE_LASTSTRIKES, "r") as f:
			lines = f.readlines()
		for l in lines:
			a = l.split(",")
			id = int(a[0])
			when = int(a[1])
			if userid==id:
				ret = a[1]
	return(int(ret))

# Write last strike called by user to local file
def logLastStrike(userid, seconds, username):
	with open(FILE_LASTSTRIKES, "a") as f:
		f.write (str(userid) + "," + str(seconds) + "," + username + "\n")


writeLog("Main loop starting...")

loops = 0
followers = api.GetFollowers()
writeLog("Updating follower list")

while True:
	# Avoid fetching followers in every loop due to rate limiting
	loops = loops + 1
	if loops == FETCH_FOLLOWERS:
		loops = 0
		followers = api.GetFollowers()
		writeLog("Updating follower list")

	processCC()
	time.sleep(LOOP_DELAY)
	writeLog("Tick")

	# Fetch last mentions to self since last one fetched
	lastid = getLastID()
	writeLog("Previous status ID fetched was " + str(lastid))
	newlastid = 0
	for mention in api.GetMentions(count=10, since_id=lastid, trim_user=False):
		mentionid = mention.id
		if mentionid > newlastid:
			newlastid = mentionid
		text = mention.text.encode('utf-8')
		userid = mention.user.id
		name = mention.user.name
		username = mention.user.screen_name
		created = int(mention.created_at_in_seconds)
		usersmentioned = mention.user_mentions

		writeLog("Fetched status ID " + str(mentionid))
		writeLog("-- Text:    " + text)
		writeLog("-- User:    " + username + " [" + str(userid) + "]")
		writeLog("-- Created: " + str(created))

		if (not username=="dronestrike") and isFollower(userid):
			writeLog("-- @" + username + " is a follower")

			period = created-getSecondsLastStrike(userid)
			if period > MINIMUM_DELAY:
				# STRIKE!
				writeLog("-- Strike!!")

				striketext = ""
				for u in usersmentioned:
					if (not u.id == userid) and (not u.screen_name=="dronestrikebot"):
						striketext = striketext + "@" + u.screen_name + " "
				writeLog("-- Targets: " + striketext)

				post1 = api.PostUpdate(striketext + "drone strike ordered by @" + username, in_reply_to_status_id=mentionid)
				time.sleep(5)
				api.PostMedia(striketext, 'dronestrike.jpg', in_reply_to_status_id=str(post1.id))
				logLastStrike(userid, created, username)
				writeLog("-- Strike ends.")
			else:
				writeLog("-- Only " + str(period) + " seconds since last one. Need " + str(MINIMUM_DELAY))
				writeLog("-- Ignoring")
		else:
			writeLog("-- @" + username + " is not a follower (or it's ourselves!)")
			writeLog("-- Ignoring")

	if newlastid > lastid:
		setLastID(newlastid)
		writeLog("New last ID is " + str(newlastid))





