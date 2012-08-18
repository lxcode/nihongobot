#!/usr/local/bin/python2.6
# -*- coding: utf-8 -*-

# Changes:
# 
# 2007-11-5:  Catch exceptions caused by regex injection, set resource to be non-random
# 2007-11-2:  set message type explicitly to "chat", and assume commands are 
#             search requests unless they match another command
# 2007-07-12: fix bug with typing notifications and newer versions of
#             Adium.
#

import xmpp
import sys
import string
import re
import time
import random

# user-configurable stuff
dictionary="/usr/local/share/dict/edict-utf-8/edict"
maxresults=50
# only appropriate that I support japanese error messages
i18n={'jp':{},'en':{}}

commands={}

# read in the dictionary
try:
    f = open(dictionary,'r')
except IOError:
    print "Error opening edict."
dict = unicode(f.read(),"utf-8")
dict = dict.split('\n')
f.close()

####################### user handlers start ##################################
i18n['en']['HELP']='Hi! I\'m a UTF-8 EDICT gateway. I can translate from English to Japanese, or from Japanese to English. You can translate words by asking "search <word>", or just typing the word.'
i18n['jp']['HELP']='こんにいちは！ぼくは UTF-8 EDICT 訳者です。 英語で日本語に(fill this in). "search"訳すします。'
def helpHandler(user,command,args,mess):
    return "HELP"

def doSearch(pattern,lines):
    matches=""
    x=0
    for line in lines:
	if x==maxresults: matches=matches + "\nResults truncated to %d. Please try a more specific query.\n"%maxresults; return matches
	if pattern.search(line):
	    matches=matches+line + "\n"; x=x+1
    return matches

i18n['en']['EMPTY']="%s"
i18n['en']['search']='%s'
def searchHandler(user,command,args,mess):

    try:
        # get our regexes ready
        # english word match
        pat1 = re.compile('[/ ]%s[/ ]'%args, re.I)
        # kana word exact match
        pat2 = re.compile(r'\[\b%s\b\]'%args, re.U)
        # kanji match
        pat3 = re.compile('^%s '%args, re.U)
        # last ditch effort
        pat4 = re.compile('%s'%args, re.I)
    except:
        return "SEARCH" ,'Cut that out.'

    #
    # Ok, this is super messy, but the idea is to keep huge numbers of
    # results from coming back. Basically, try all 4 lookup types in
    # order, and only go onto the next one if the previous failed to
    # yield results.
    #

    results = doSearch(pat1,dict)
    if results=="": results = doSearch(pat2,dict)
    if results=="": results = doSearch(pat3,dict)
    if results=="": results = doSearch(pat4,dict)
    if results=="": results="Sorry, I can\'t find that word."

    return "SEARCH",'Matches for "%s":\n\n%s'%(args, results)

####################### user handlers stop ###################################
######################## bot logic start #####################################
i18n['en']["UNKNOWN COMMAND"]='Unknown command "%s". Try "help".'
i18n['jp']["UNKNOWN COMMAND"]='コマンドは正しくありません　− %s'
i18n['en']["UNKNOWN USER"]="I do not know you. Register first."
i18n['jp']["UNKNOWN USER"]="登録して下さい。"

def messageCB(conn,mess):
    text=mess.getBody()
    user=mess.getFrom()
    user.lang='en'
    # make sure text isn't null, like with typing notification messages
    # from Adium
    if text:
        if text.find(' ')+1: 
            command,args=text.split(' ',1)
        else: 
            command,args=text,''
        cmd=command.lower()

        if commands.has_key(cmd): 
            reply=commands[cmd](user,command,args,mess)
        #else: reply=("UNKNOWN COMMAND",cmd)
        else: 
            # if no command matches, assume it's a search.
            reply=searchHandler(user,"search",command,mess)

        if type(reply)==type(()):
            key,args=reply
            if i18n[user.lang].has_key(key): pat=i18n[user.lang][key]
            elif i18n['en'].has_key(key): pat=i18n['en'][key]
            else: pat="%s"
            if type(pat)==type(''): reply=pat%args
            else: reply=pat(**args)
        else:
            try: reply=i18n[user.lang][reply]
            except KeyError:
                try: reply=i18n['en'][reply]
                except KeyError: pass
        if reply: conn.send(xmpp.Message(mess.getFrom(), body=reply, typ='chat'))

for i in globals().keys():
    if i[-7:]=='Handler' and i[:-7].lower()==i[:-7]: commands[i[:-7]]=globals()[i]

# Handle subscription/unsubscription requests

def presenceCB(conn,pres):
    type=pres.getType()
    user=pres.getFrom()
    if type=='subscribe':
    	conn.send(xmpp.Presence(user,'subscribed'))
    if type=='unsubscribe':
    	conn.send(xmpp.Presence(user,'unsubscribed'))

######################### bot logic stop #####################################

def connect():
    # This is here rather than the cmdline to prevent it being in process 
    # environment.
    password=""
    jid=xmpp.JID(sys.argv[1])
    user,server,password=jid.getNode(),jid.getDomain(),password
    print user
    print server
    print password
    conn=xmpp.Client(server)#,debug=[])
    conres=conn.connect()
    conn.RegisterDisconnectHandler(disconnectCB)

    if not conres:
        print "Unable to connect to server %s!"%server
        sys.exit(1)
    if conres<>'tls':
        print "Warning: unable to establish secure connection - TLS failed!"
    authres=conn.auth(user,password,"Redundancy")
    if not authres:
        print "Unable to authorize on %s - check login/password."%server
        sys.exit(1)
    if authres<>'sasl':
        print "Warning: unable to perform SASL auth os %s. Old authentication method used!"%server
    conn.RegisterHandler('message',messageCB)
    conn.RegisterHandler('presence',presenceCB)
    conn.sendInitPresence()
    print "Bot started."
    return conn

def disconnectCB():
    #time.sleep(120)
    #connect()
    sys.exit(1)

def StepOn(conn):
    try:
        conn.Process(1)
	# I can't believe I'm doing this...but I seem to be hitting TCP conn timeouts
        chance = random.randint(0,50)
        if chance == 37:
#            conn.sendPresence("redundancy.redundancy.org", 'online')
	    # thanks js
            try:
                iq = xmpp.Iq()
                iq.setTag('x', namespace='urn:xmpp:ping')
                iq.setTo('lx@redundancy.redundancy.org')
                iq.setType('get')
                conn.send(iq)
            except KeyboardInterrupt, sslerror: return 0
    except KeyboardInterrupt, sslerror: return 0
    return 1

def GoOn(conn):
    while StepOn(conn): pass

if len(sys.argv)!=2:
    print "Usage: " + sys.argv[0] + " username@server.net"
else:
    conn=connect()

    GoOn(conn)
    #conn.sendPresence("redundancy.redundancy.org",'offline')
    conn.disconnect()
    sys.exit(0)

