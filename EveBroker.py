#!/usr/bin/env python3

"""
EveBroker
Calculate your profit margin from buy to sell orders based on market skills and entity standings.
Copyright (C) 2019 Christian Rickert <mail@crickert.de>

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
Copyright © CCP hf. <info@ccpgames.com> 1997-2019
"""


# imports

import base64
import hashlib
import os
import random
import secrets
import sys
import urllib.parse
import webbrowser
import ccp_esi


# variables

AUTHOR = "Copyright (C) 2019 Christian Rickert"
DISCLAIMER = "EveBroker is distributed in the hope that it will be useful, but it comes w/o\nany guarantee or warranty.  This program is free software; you can redistribute\nit and/or modify it under the terms of the GNU General Public License:"
INTERMEDIATELINE = '{0:}'.format("Calculate your profit margin from buy to sell orders based on market skills\nand entity standings. Checks your character's docking location for NPC fees.")
SEPARBOLD = 79*'='
SEPARNORM = 79*'-'
SOFTWARE = "EveBroker"
URL = "https://www.gnu.org/licenses/gpl-2.0.en.html"
VERSION = "version 2.0,"  # (2019-10-20)
GREETER = '{0:<{w0}}{1:<{w1}}{2:<{w2}}'.format(SOFTWARE, VERSION, AUTHOR, w0=len(SOFTWARE)+1, w1=len(VERSION)+1, w2=len(AUTHOR)+1)


# functions

def apply_skills(basevalue=0.0, multiplier=0.0, level=0, resists=False, maxvalue=1):
    """ Calculates and returns the skill-modified base value. """
    if resists:  # calculation based on difference between basevalue and maxvalue
        skillvalue = float(maxvalue) - (1.00 - (float(level) * float(multiplier))) * (float(maxvalue) - float(basevalue))
    else:  # calculation based on basevalue only
        while level:
            basevalue = float(basevalue) + float(multiplier) * float(basevalue)
            level -= 1
        skillvalue = basevalue
    return skillvalue

def askboolean(dlabel="custom boolean", dval=True):
    """ Returns a boolean provided by the user. """
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

def create_pcke_challenge(random_string=None):
    """ Returns a Base64 encoded string as PCKE code challenge from a random input string. """
    string_hash = hashlib.sha256()
    string_hash.update(random_string)
    string_hash_digest = string_hash.digest()
    return base64.urlsafe_b64encode(string_hash_digest).decode().replace("=", "")


# main routine

print('{0:^79}'.format(SEPARBOLD) + os.linesep)
print('{0:^79}'.format(GREETER) + os.linesep)
print('{0:^79}'.format(INTERMEDIATELINE) + os.linesep)
print('{0:^79}'.format(DISCLAIMER) + os.linesep)
print('{0:^79}'.format(URL) + os.linesep)
print('{0:^79}'.format(SEPARBOLD) + os.linesep)

# Authenticate with the EVE Swagger Interface
# For details, see: https://github.com/esi/esi-docs/

# Authentication procedure with SSO, OAuth 2.0 flow
sys.stdout.write(">> Single Sign-On (SSO)... ")
sys.stdout.flush()

REDIRECT_URI = "http://localhost:1234"
CLIENT_ID = "c7e50f4b47af437280f52739ce26df91"
SCOPE = "esi-location.read_location.v1 esi-skills.read_skills.v1 esi-wallet.read_character_wallet.v1 esi-characters.read_standings.v1"

try:
    while True:  # interval defined by listener timeout
        try:
            # Redirect user to the authorization site to log in
            VERIFIER = base64.urlsafe_b64encode(secrets.token_bytes(32))  # we need this for later
            CHALLENGE = create_pcke_challenge(VERIFIER)
            STATE = str(random.getrandbits(32))
            SSO_URI = "https://login.eveonline.com/v2/oauth/authorize/"
            SSO_URL = SSO_URI + "?response_type=code" + "&redirect_uri=" + REDIRECT_URI + "&client_id=" + CLIENT_ID + "&scope=" + SCOPE + "&code_challenge=" + CHALLENGE + "&code_challenge_method=S256" + "&state=" + STATE
            webbrowser.open(SSO_URL, new=2, autoraise=True)

            # Start local server to listen for callback, i.e. receive the authorization code
            ADDRESS = "localhost"
            PORT = 1234
            AUTH_CODE = ccp_esi.get_listener(ADDRESS, PORT).split('&')[0][11:]

            # Request the access token from the remote server by providing the authentication code received earlier
            ACC_URL = "https://login.eveonline.com/v2/oauth/token"
            ACC_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'login.eveonline.com'}
            ACC_DATA = {'grant_type': 'authorization_code', 'client_id': CLIENT_ID, 'code': AUTH_CODE, 'code_verifier': VERIFIER}
            ACC_RESPONSE = ccp_esi.get_request(ACC_URL, ACC_HEADERS, data=ACC_DATA)  # access_token, expires_in, token_type, refresh_token
            ACC_TOKEN = ACC_RESPONSE['access_token']
        except urllib.error.HTTPError as http_error:  # communication failed
            print(http_error)
        else:
            break

    # Redirect to the Single Sign-On and get the character ID
    ID_URL = "https://login.eveonline.com/oauth/verify"
    ID_KEY = "Bearer " + str(ACC_TOKEN)
    ID_HEADERS = {'User-Agent': 'Python-urllib/3.7', 'Authorization': ID_KEY, 'Host': 'login.eveonline.com'}
    ID_RESPONSE = ccp_esi.get_request(ID_URL, ID_HEADERS)  # CharacterID, CharacterName, ExpiresOn, Scopes, TokenType, CharacterOwnerHash
    CHARACTER_ID = ID_RESPONSE['CharacterID']
    sys.stdout.write("\n   SSO: " + str(ID_RESPONSE['CharacterName']) + "\n")
    sys.stdout.write(9 * "\t" + "   [OK]\n")
    sys.stdout.flush()

    # Access the EVE Swagger Interface
    sys.stdout.write(">> EVE Swagger Interface (ESI)... ")
    sys.stdout.flush()
    ESI_URL = "https://esi.evetech.net/latest"
    ESI_KEY = ID_KEY

    # Get character skills
    ESI_HEADERS = {'Accept': 'application/json', 'Authorization': ID_KEY}
    CHARACTER_SKILLS = ccp_esi.get_request(ESI_URL + "/characters/" + str(CHARACTER_ID) + "/skills/", ESI_HEADERS)
    ACCOUNTING_LEVEL = ccp_esi.read_api(CHARACTER_SKILLS['skills'], 'active_skill_level', ('skill_id', 16622)) or 0
    sys.stdout.write("\n   ESI: Accounting level" + 1 * "\t" + str(ACCOUNTING_LEVEL))
    sys.stdout.flush()
    BROKER_RELATIONS_LEVEL = ccp_esi.read_api(CHARACTER_SKILLS['skills'], 'active_skill_level', ('skill_id', 3446)) or 0
    sys.stdout.write("\n   ESI: Broker relations level" + 1 * "\t" + str(BROKER_RELATIONS_LEVEL))
    sys.stdout.flush()
    CONNECTIONS_LEVEL = ccp_esi.read_api(CHARACTER_SKILLS['skills'], 'active_skill_level', ('skill_id', 3359)) or 0
    sys.stdout.write("\n   ESI: Connections level" + 1 * "\t" + str(CONNECTIONS_LEVEL))
    sys.stdout.flush()
    MARGIN_TRADING_LEVEL = ccp_esi.read_api(CHARACTER_SKILLS['skills'], 'active_skill_level', ('skill_id', 16597)) or 0
    sys.stdout.write("\n   ESI: Margin trading level" + 1 * "\t" + str(MARGIN_TRADING_LEVEL))
    sys.stdout.flush()

    # Get character standings from agents, NPC corporations, and factions
    ESI_HEADERS = {'Accept': 'application/json', 'Authorization': ID_KEY}
    CHARACTER_STANDINGS = ccp_esi.get_request(ESI_URL + "/characters/" + str(CHARACTER_ID) + "/standings/", ESI_HEADERS)
    sys.stdout.write("\n   ESI: NPC standings" + 2 * "\t" + str(len(CHARACTER_STANDINGS)))
    sys.stdout.flush()

    # Get npc station information from character location
    try:
        ESI_HEADERS = {'Accept': 'application/json', 'Authorization': ID_KEY}
        STATION_ID = ccp_esi.get_request(ESI_URL + "/characters/" + str(CHARACTER_ID) + "/location/", ESI_HEADERS)['station_id']
        sys.stdout.write("\n   ESI: NPC station ID" + 2 * "\t" + "(" + str(STATION_ID) + ")")
        ESI_HEADERS = {'Accept': 'application/json'}
        STATION = ccp_esi.get_request(ESI_URL + "/universe/stations/" + str(STATION_ID) + "/", ESI_HEADERS)
        STATION_CORPORATION = STATION['owner']
        STATION_NAME = STATION['name']
        sys.stdout.write("\n   ESI: NPC station name\t" + str(STATION_NAME))
    except KeyError:  # undocked or non-NPC structure
        sys.stdout.write("\n   ESI: NPC station ID" + 2 * "\t" + "(default)")
        STATION_CORPORATION = 1000035  # Caldary Navy
        sys.stdout.write("\n   ESI: NPC station name\t" + "Jita IV - Moon 4 - Caldari Navy Assembly Plant")
    sys.stdout.flush()

    # Get station corporation
    ESI_HEADERS = {'Accept': 'application/json'}
    CORPORATIONS = ccp_esi.get_request(ESI_URL + "/corporations/" + str(STATION_CORPORATION) + "/", ESI_HEADERS)
    CORPORATION_NAME = CORPORATIONS['name']
    sys.stdout.write("\n   ESI: NPC corporation" + 2 * "\t" + str(CORPORATION_NAME))
    sys.stdout.flush()

    # Get station faction
    ESI_HEADERS = {'Accept': 'application/json'}
    UNIVERSE_FACTIONS = ccp_esi.get_request(ESI_URL + "/universe/factions/", ESI_HEADERS)
    KNOWN_CORPORATIONS = []
    try:
        for FACTIONS in UNIVERSE_FACTIONS:
            KNOWN_CORPORATIONS.append(FACTIONS['corporation_id'])
    except KeyError:  # unknown faction has no corporation id
        pass
    if STATION_CORPORATION in KNOWN_CORPORATIONS:
        STATION_FACTION = ccp_esi.read_api(UNIVERSE_FACTIONS, 'faction_id', ('corporation_id', STATION_CORPORATION))
        FACTION_NAME = ccp_esi.read_api(UNIVERSE_FACTIONS, 'name', ('corporation_id', STATION_CORPORATION))
    else:
        STATION_FACTION = 500001
        FACTION_NAME = "Caldari State"
    sys.stdout.write("\n   ESI: NPC faction" + 2 * "\t" + str(FACTION_NAME))

    # Get character wallet balance
    ESI_HEADERS = {'Accept': 'application/json', 'Authorization': ID_KEY}
    WALLET_BALANCE = ccp_esi.get_request(ESI_URL + "/characters/" + str(CHARACTER_ID) + "/wallet/", ESI_HEADERS) or 0.0  # server will return 'None', if balance is Zero
    sys.stdout.write("\n   ESI: Wallet balance" + 2 * "\t" + "{:<,.2f} ISK".format(WALLET_BALANCE))
    sys.stdout.write("\n" + 9 * "\t" + "   [OK]\n")
    sys.stdout.flush()

    # Calculate market fees
    CORPORATION_STANDINGS = ccp_esi.read_api(CHARACTER_STANDINGS, 'standing', ('from_TYPE', 'npc_corp'), ('from_id', STATION_CORPORATION)) or 0.0
    #CORPORATION_STANDINGS = apply_skills(CORPORATION_STANDINGS, 0.04, CONNECTIONS_LEVEL, True, 10.0) # CCP uses raw standings
    FACTION_STANDINGS = ccp_esi.read_api(CHARACTER_STANDINGS, 'standing', ('from_TYPE', 'npc_corp'), ('from_id', STATION_FACTION)) or 0.0
    #FACTION_STANDINGS = apply_skills(FACTION_STANDINGS, 0.04, CONNECTIONS_LEVEL, True, 10.0) # CCP uses raw standings
    sys.stdout.write("Trading skills:" + 2 * "\t" + "    ROOKIE\t        YOU\t        EXPERT" + os.linesep)
    BROKER_FEE = (5.0 - (0.3 * BROKER_RELATIONS_LEVEL) - (0.03 * FACTION_STANDINGS) - (0.02 * CORPORATION_STANDINGS))/100.0
    print("Brokers fee:" + 2 * "\t" + "  {: >9.4%}\t    {: >9.4%}\t      {: >9.4%}".format(0.05, BROKER_FEE, 0.03))
    MARGIN_FEE = apply_skills(1.0, -0.25, MARGIN_TRADING_LEVEL)
    print("Margin Trading fee:\t  {: >9.4%}\t    {: >9.4%}\t      {: >9.4%}".format(1.000000, MARGIN_FEE, 0.237305))
    TRANSACTION_TAX = apply_skills(0.05, -0.11, ACCOUNTING_LEVEL)
    print("Transaction tax:\t  {: >9.4%}\t    {: >9.4%}\t      {: >9.4%}".format(0.05, TRANSACTION_TAX, 0.0225))

    # Calculate margin
    while True:
        try:
            MARGIN = 0.00
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
            MARGIN -= BROKER_FEE*BUY_ORDER if BROKER_FEE*BUY_ORDER > 100.00 else 100.00  # minimum fee
            print("{: >+20,.2f} ISK".format(-(BROKER_FEE*BUY_ORDER) if BROKER_FEE*BUY_ORDER > 100.00 else -100.00) + "  Brokers fee" + 2 * "\t" + "|" + "{: > 20,.2f} ISK".format(MARGIN))
            MARGIN -= MARGIN_FEE*BUY_ORDER
            print("{: >+20,.2f} ISK".format(-(MARGIN_FEE*BUY_ORDER)) + "  Margin trading\t|" + "{: > 20,.2f} ISK".format(MARGIN))
            MARGIN -= BUY_ORDER-MARGIN_FEE*BUY_ORDER
            print("{: >+20,.2f} ISK".format(-(BUY_ORDER-MARGIN_FEE*BUY_ORDER)) + "  ** Item bought **\t|" + "{: > 20,.2f} ISK".format(MARGIN))
            MARGIN -= BROKER_FEE*SELL_ORDER if BROKER_FEE*SELL_ORDER > 100.00 else 100.00
            print("{: >+20,.2f} ISK".format(-(BROKER_FEE*SELL_ORDER) if BROKER_FEE*SELL_ORDER > 100.00 else -100.00) + "  Brokers fee" + 2 * "\t" + "|" + "{: > 20,.2f} ISK".format(MARGIN))
            MARGIN -= TRANSACTION_TAX*SELL_ORDER
            print("{: >+20,.2f} ISK".format(-(TRANSACTION_TAX*SELL_ORDER)) + "  Transaction tax\t|" + "{: > 20,.2f} ISK".format(MARGIN))
            MARGIN += SELL_ORDER # resulting profit
            sys.stdout.write("{: >+20,.2f} ISK".format(+SELL_ORDER) + "  ** Item sold **\t|" + "{: > 20,.2f} ISK".format(MARGIN))
            if MARGIN >= 0.00:
                if MARGIN >= 0.10 * BUY_ORDER: # margin is at least 10% of buy order
                    sys.stdout.write(" (+++)" + os.linesep)
                elif MARGIN >= 0.05 * BUY_ORDER: # margin is at least 5% of buy order
                    sys.stdout.write(" (++)" + os.linesep)
                elif MARGIN >= 0.01 * BUY_ORDER: # margin is at least 1% of buy order
                    sys.stdout.write(" (+)" + os.linesep)
                elif MARGIN >= 0.00: # margin is less than 1% of buy order
                    sys.stdout.write(" (o)" + os.linesep)
            elif MARGIN < 0.00: # margin is negative, you lose money
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
