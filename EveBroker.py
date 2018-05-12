#!/usr/bin/env python3

'''
EveBroker
Calculate your profit margin from buy to sell orders based on market skills and entity standings.
Copyright (C) 2018 Christian Rickert <mail@crickert.de>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
----------------------------------------------------------------------------------------------------
Eve Online
Copyright © CCP hf. <info@ccpgames.com> 1997-2018
'''


# imports

import base64
import os
import random
import sys
import urllib.parse
import webbrowser
import ccp_esi


# variables

AUTHOR = "Copyright (C) 2018 Christian Rickert"
DISCLAIMER = "EveBroker is distributed in the hope that it will be useful, but it comes w/o\nany guarantee or warranty.  This program is free software; you can redistribute\nit and/or modify it under the terms of the GNU General Public License:"
INTERMEDIATELINE = '{0:}'.format("Calculate your profit margin from buy to sell orders based on market skills\nand entity standings. Checks your character's docking location for NPC fees.")
SEPARBOLD = 79*'='
SEPARNORM = 79*'-'
SOFTWARE = "EveBroker"
URL = "https://www.gnu.org/licenses/gpl-2.0.en.html"
VERSION = "version 1.0,"  # (2018-05-11)
GREETER = '{0:<{w0}}{1:<{w1}}{2:<{w2}}'.format(SOFTWARE, VERSION, AUTHOR, w0=len(SOFTWARE)+1, w1=len(VERSION)+1, w2=len(AUTHOR)+1)


# functions

def apply_skills(basevalue=0.0, multiplier=0.0, level=0, resists=False, maxvalue=1):
    """ Calculates and returns the skill-modified base value """
    if resists:  # calculation based on difference between basevalue and maxvalue
        skillvalue = float(maxvalue) - (1.00 - (float(level) * float(multiplier))) * (float(maxvalue) - float(basevalue))
    else:  # calculation based on basevalue only
        while level:
            basevalue = float(basevalue) + float(multiplier) * float(basevalue)
            level -= 1
        skillvalue = basevalue
    return skillvalue

def askboolean(dlabel="custom boolean", dval=True):
    """Returns a boolean provided by the user."""
    if dval:  # True
        dstr = "Y/n"
    else:  # False
        dstr = "y/N"
    while True:
        uchoice = input(dlabel + " [" + dstr + "]: ") or dstr
        if uchoice.lower().startswith("y") and not uchoice.endswith("N"):
            print("True")
            return True  # break
        elif (uchoice.endswith("N") and not uchoice.startswith("Y")) or uchoice.lower().startswith("n"):
            print("False")
            return False  # break
        else:
            continue


# main routine

print('{0:^79}'.format(SEPARBOLD) + os.linesep)
print('{0:^79}'.format(GREETER) + os.linesep)
print('{0:^79}'.format(INTERMEDIATELINE) + os.linesep)
print('{0:^79}'.format(DISCLAIMER) + os.linesep)
print('{0:^79}'.format(URL) + os.linesep)
print('{0:^79}'.format(SEPARBOLD) + os.linesep)

# Authenticate with the EVE Swagger Interface
# For details, see: https://eveonline-third-party-documentation.readthedocs.io/en/latest/sso/

# Authentication procedure with SSO
sys.stdout.write(">> Single Sign-On\t (SSO)... ")
sys.stdout.flush()
SSO_URI = "https://login.eveonline.com/oauth/authorize/"
RESPONSE_TYPE = "code"
REDIRECT_URI = "http://localhost:1234"
CLIENT_ID = "c7e50f4b47af437280f52739ce26df91"
SCOPE = "esi-location.read_location.v1 esi-skills.read_skills.v1 esi-wallet.read_character_wallet.v1 esi-characters.read_standings.v1"
SECRET_KEY = "nMkEVIYrIkjTBN6g5M2m1lcxrtoDRA2eRMg6Onr8" # super secret
AUTH_CODE = ""

try:
    while True:  # interval defined by listener timeout
        try:
            # Redirect user to the authorization site to log in
            STATE = str(random.getrandbits(32))
            SSO_URL = SSO_URI + "?response_type=" + RESPONSE_TYPE + "&redirect_uri=" + REDIRECT_URI + "&client_id=" + CLIENT_ID + "&scope=" + SCOPE + "&state=" + STATE
            webbrowser.open(SSO_URL, new=2, autoraise=True)

            # Start local server to listen for callback, i.e. receive the authorization code
            ADDRESS = "localhost"
            PORT = 1234
            AUTH_CODE = ccp_esi.get_listener(ADDRESS, PORT)[11:76]

            # Request the access token from the remote server by providing the authentication code received earlier
            AUTH_URL = "https://login.eveonline.com/oauth/token"
            AUTH_KEY = "Basic " + base64.b64encode((CLIENT_ID + ":" + SECRET_KEY).encode(encoding="utf-8", errors="replace")).decode(encoding="utf-8", errors="replace")
            AUTH_HEADERS = {'Authorization': AUTH_KEY, 'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'login.eveonline.com'}
            DATA = {'grant_TYPE': 'authorization_code', 'code': AUTH_CODE}
            AUTH_RESPONSE = ccp_esi.get_request(AUTH_URL, AUTH_HEADERS, data=DATA)  # access_token, token_type, expires_in, refresh_token
            AUTH_TOKEN = AUTH_RESPONSE['access_token']
        except urllib.error.HTTPError:  # communication problem or negative reply
            continue
        else:
            break

    # Get the character ID
    ID_URL = "https://login.eveonline.com/oauth/verify"
    ID_KEY = "Bearer " + str(AUTH_TOKEN)
    ID_HEADERS = {'User-Agent': 'Python-urllib/3.6', 'Authorization': ID_KEY, 'Host': 'login.eveonline.com'}
    ID_RESPONSE = ccp_esi.get_request(ID_URL, ID_HEADERS)  # CharacterID, CharacterName, ExpiresOn, Scopes, TokenType, CharacterOwnerHash
    CHARACTER_ID = ID_RESPONSE['CharacterID']
    sys.stdout.write("\n" + 3 * "\t" + "  SSO: " + str(ID_RESPONSE['CharacterName']) + "\n")
    sys.stdout.write(9 * "\t" + "   [OK]\n")
    sys.stdout.flush()

    ## Access the EVE Swagger Interface
    sys.stdout.write(">> EVE Swagger Interface (ESI)... ")
    sys.stdout.flush()
    ESI_URL = "https://esi.evetech.net/latest"
    ESI_KEY = ID_KEY

    # Get character skills
    ESI_HEADERS = {'Accept': 'application/json', 'Authorization': ID_KEY}
    CHARACTER_SKILLS = ccp_esi.get_request(ESI_URL + "/characters/" + str(CHARACTER_ID) + "/skills/", ESI_HEADERS)
    ACCOUNTING_LEVEL = ccp_esi.read_api(CHARACTER_SKILLS['skills'], 'active_skill_level', ('skill_id', 16622)) or 0
    sys.stdout.write("\n" + 3 * "\t" + "  ESI: Accounting level:" + 1 * "\t" + str(ACCOUNTING_LEVEL))
    sys.stdout.flush()
    BROKER_RELATIONS_LEVEL = ccp_esi.read_api(CHARACTER_SKILLS['skills'], 'active_skill_level', ('skill_id', 3446)) or 0
    sys.stdout.write("\n" + 3 * "\t" + "  ESI: Broker relations level:" + 1 * "\t" + str(BROKER_RELATIONS_LEVEL))
    sys.stdout.flush()
    CONNECTIONS_LEVEL = ccp_esi.read_api(CHARACTER_SKILLS['skills'], 'active_skill_level', ('skill_id', 3359)) or 0
    sys.stdout.write("\n" + 3 * "\t" + "  ESI: Connections level:" + 1 * "\t" + str(CONNECTIONS_LEVEL))
    sys.stdout.flush()
    MARGIN_TRADING_LEVEL = ccp_esi.read_api(CHARACTER_SKILLS['skills'], 'active_skill_level', ('skill_id', 16597)) or 0
    sys.stdout.write("\n" + 3 * "\t" + "  ESI: Margin trading level:" + 1 * "\t" + str(MARGIN_TRADING_LEVEL))
    sys.stdout.flush()

    # Get character standings
    ESI_HEADERS = {'Accept': 'application/json', 'Authorization': ID_KEY}
    CHARACTER_STANDINGS = ccp_esi.get_request(ESI_URL + "/characters/" + str(CHARACTER_ID) + "/standings/", ESI_HEADERS)
    sys.stdout.write("\n" + 3 * "\t" + "  ESI: Standings:" + 2 * "\t" + "(" + str(len(CHARACTER_STANDINGS)) + ")")
    sys.stdout.flush()

    # Get character wallet balance
    ESI_HEADERS = {'Accept': 'application/json', 'Authorization': ID_KEY}
    WALLET_BALANCE = ccp_esi.get_request(ESI_URL + "/characters/" + str(CHARACTER_ID) + "/wallet/", ESI_HEADERS)
    sys.stdout.write("\n" + 3 * "\t" + "  ESI: Wallet Balance:" + 2 * "\t" + "{:<,.2f} ISK".format(WALLET_BALANCE))
    sys.stdout.flush()

    # Get character npc station
    ESI_HEADERS = {'Accept': 'application/json', 'Authorization': ID_KEY}
    try:
        STATION_ID = ccp_esi.get_request(ESI_URL + "/characters/" + str(CHARACTER_ID) + "/location/", ESI_HEADERS)['STATION_ID']
    except KeyError:  # character might be undocked or docked in a non-NPC station, defaulting to Jita-4-4
        STATION_ID = 60003760
    sys.stdout.write("\n" + 3 * "\t" + "  ESI: NPC STATION ID:" + 2 * "\t" + "(" + str(STATION_ID) + ")")
    sys.stdout.flush()

    # Get station name and corporation
    ESI_HEADERS = {'Accept': 'application/json'}
    STATION = ccp_esi.get_request(ESI_URL + "/universe/stations/" + str(STATION_ID) + "/", ESI_HEADERS)
    sys.stdout.write("\r" + 3 * "\t" + "  \"" + str(STATION['name']) + "\"")
    sys.stdout.flush()

    # Get station faction
    ESI_HEADERS = {'Accept': 'application/json'}
    UNIVERSE_FACTIONS = ccp_esi.get_request(ESI_URL + "/universe/factions/", ESI_HEADERS)
    STATION_FACTION = ccp_esi.read_api(UNIVERSE_FACTIONS, 'faction_id', ('corporation_id', STATION['owner']))

    # Get character standings
    CORPORATION_STANDINGS = ccp_esi.read_api(CHARACTER_STANDINGS, 'standing', ('from_TYPE', 'npc_corp'), ('from_id', STATION['owner'])) or 0.0
    #CORPORATION_STANDINGS = apply_skills(CORPORATION_STANDINGS, 0.04, CONNECTIONS_LEVEL, True, 10.0) # CCP uses raw standings
    FACTION_STANDINGS = ccp_esi.read_api(CHARACTER_STANDINGS, 'standing', ('from_TYPE', 'npc_corp'), ('from_id', STATION_FACTION)) or 0.0
    #FACTION_STANDINGS = apply_skills(FACTION_STANDINGS, 0.04, CONNECTIONS_LEVEL, True, 10.0) # CCP uses raw standings
    sys.stdout.write("\n" + 9 * "\t" + "   [OK]\n")
    sys.stdout.flush()

    # Calculate fees
    sys.stdout.write("Trading Character:\t    ROOKIE\t        YOU\t        EXPERT" + os.linesep)
    BROKER_FEE = (3.0 - (0.1 * BROKER_RELATIONS_LEVEL) - (0.03 * FACTION_STANDINGS) - (0.02 * CORPORATION_STANDINGS))/100.0
    print("\nBrokers Fee:" + 2 * "\t" + "  {: >9.4%}\t    {: >9.4%}\t      {: >9.4%}".format(0.03, BROKER_FEE, 0.02))
    MARGIN_FEE = apply_skills(1.0, -0.25, MARGIN_TRADING_LEVEL)
    print("Margin Trading Fee:\t  {: >9.4%}\t    {: >9.4%}\t      {: >9.4%}".format(1.000000, MARGIN_FEE, 0.237305))
    TRANSACTION_TAX = 0.02 - (0.01 / 5.00) * ACCOUNTING_LEVEL
    print("Transaction Tax:\t  {: >9.4%}\t    {: >9.4%}\t      {: >9.4%}".format(0.02, TRANSACTION_TAX, 0.01))

    # Calculate margin
    while True:
        try:
            BALANCE = 0.00
            BUY_ORDER = -1.00
            SELL_ORDER = -1.00
            print('{0:^79}'.format(SEPARNORM))
            print("Please enter your orders:")
            while BUY_ORDER < 0.00:
                BUY_ORDER = float(input("Buy price  [ISK]:\t  "))
            while SELL_ORDER < 0.00:
                SELL_ORDER = float(input("Sell price [ISK]:\t  "))
            print('{0:^79}'.format(SEPARNORM))
            print("" + 2 * "\t" + "   Transactions " + 2 * "\t" + "|\t  Profit margin")
            print('{0:^79}'.format(SEPARNORM))
            BALANCE -= BROKER_FEE*BUY_ORDER if BROKER_FEE*BUY_ORDER > 100.00 else 100.00  # minimum fee
            print("{: >+20,.2f} ISK".format(-(BROKER_FEE*BUY_ORDER) if BROKER_FEE*BUY_ORDER > 100.00 else -100.00) + "  Brokers Fee" + 2 * "\t" + "|" + "{: > 20,.2f} ISK".format(BALANCE))
            BALANCE -= MARGIN_FEE*BUY_ORDER
            print("{: >+20,.2f} ISK".format(-(MARGIN_FEE*BUY_ORDER)) + "  Margin Trade" + 2 * "\t" + "|" + "{: > 20,.2f} ISK".format(BALANCE))
            BALANCE -= BUY_ORDER-MARGIN_FEE*BUY_ORDER
            print("{: >+20,.2f} ISK".format(-(BUY_ORDER-MARGIN_FEE*BUY_ORDER)) + "  ** Item bought **\t|" + "{: > 20,.2f} ISK".format(BALANCE))
            BALANCE -= BROKER_FEE*SELL_ORDER if BROKER_FEE*SELL_ORDER > 100.00 else 100.00
            print("{: >+20,.2f} ISK".format(-(BROKER_FEE*SELL_ORDER) if BROKER_FEE*SELL_ORDER > 100.00 else -100.00) + "  Brokers Fee" + 2 * "\t" + "|" + "{: > 20,.2f} ISK".format(BALANCE))
            BALANCE -= TRANSACTION_TAX*SELL_ORDER
            print("{: >+20,.2f} ISK".format(-(TRANSACTION_TAX*SELL_ORDER)) + "  Transaction Tax\t|" + "{: > 20,.2f} ISK".format(BALANCE))
            BALANCE += SELL_ORDER # resulting profit
            sys.stdout.write("{: >+20,.2f} ISK".format(+SELL_ORDER) + "  ** Item sold **\t|" + "{: > 20,.2f} ISK".format(BALANCE))
            if BALANCE >= 0.00:
                if BALANCE >= 0.10 * BUY_ORDER: # margin is at least 10% of buy order
                    sys.stdout.write(" (+++)" + os.linesep)
                elif BALANCE >= 0.05 * BUY_ORDER: # margin is at least 5% of buy order
                    sys.stdout.write(" (++)" + os.linesep)
                elif BALANCE >= 0.01 * BUY_ORDER: # margin is at least 1% of buy order
                    sys.stdout.write(" (+)" + os.linesep)
                elif BALANCE >= 0.00: # margin is less than 1% of buy order
                    sys.stdout.write(" (o)" + os.linesep)
            elif BALANCE < 0.00: # margin is negative, you lose money
                sys.stdout.write(" (-)" + os.linesep)
            print('{0:^79}'.format(SEPARBOLD))
            sys.stdout.write("   (+++): >=10%, (++): >=5%, (+): >=1%, (o): >= 0%, (-): < 0% profit margin.\n")
        except ValueError:
            continue
        else:
            CONTINUE = askboolean("\nDo you want to continue?", True)
            if CONTINUE:
                continue
            else:
                break
except KeyboardInterrupt as kerr:  # user canceled
    sys.stdout.write("\n" + 9*"\t" + "   [KO]")
    print("\r   ## Run skipped. Canceled by user.")
except Exception as uerr:  # unknown error
    sys.stdout.write("\n" + 9*"\t" + "   [ER]")
    print("\r   ## Run failed. Error was: {0}".format(uerr) + ".")

WAIT = input("\r\nPress ENTER to end this program.")
