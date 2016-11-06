#! /usr/bin/python

"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""


import re
import sys
import urllib
import httplib
import os.path
import sqlite3 as sql
import xml.etree.ElementTree as ElementTree


import key
import cache
import update
import database
import container
import blueprint


def isEnabled(elm):    
    return elm.get('enabled') in ['true', 'True', '1', 'yes', 'Yes', None]



class FakeContainer:
    
    def __init__(self, contents):
        self.name = "Fake Container."
        self.contents = contents


def main(userconfig):
    
    versionfile = open('version', 'r')
    version = versionfile.read()
    versionfile.close()
    
    print("")
    print("Collective Refining Program")
    print("Version: " + version)
    print("")

    print('Using userconfig:\t' + userconfig)
    
    userconfig = ElementTree.parse(open(userconfig, 'r'))

    configfile = userconfig.findtext(".//config")

    print('Using config file:\t' + configfile)

    configtree = ElementTree.parse(open(configfile, 'r'))

    db_file = configtree.findtext(".//updates/database/filename")
    cache_file = configtree.findtext("./cache/filename")
    cache_directory = configtree.findtext("./cache/directory")

    print("")
    print("   Database file:\t" + db_file)
    print("   Cache directory:\t" + cache_directory)
    print("   Cache file:\t\t" + cache_file)
    print("")

    cache.initialize(configtree, userconfig, cache_directory, cache_file)

    ## Good, do we need an update? 
    
    print("")
    print("Checking for software updates...")

    if cache.checkUpdateTimer('core'):
        update.update(configtree)
    
    print("")    
    print("Checking for EVE online database updates...")

    if cache.checkUpdateTimer('database'):
        database.update(configtree)

    # Load the game data.
    
    blueprint.initialize(configtree)
    container.initialize(configtree)
    database.initialize(configtree)
    
    ## All right - initialize the keys. 

    keys = []

    for elm in userconfig.iter('apikey'):

        if not isEnabled(elm): continue
        
        keys += [key.fromXML(elm)]

    print("")
    print("Requesting AssetLists...")
    
    containers = []

    for k in keys:
        containers += cache.getContainers(k)

    
    print("")
    print("Fetching Blueprint List...")

    blueprints = []

    for k in keys:
        blueprints += cache.getBlueprints(k)

    
    for c in containers:
        c.addBlueprintInfo(blueprints)
    
    print("")
    print("Generating Output...")        

    for c in containers:

        if not c.contents:
            continue

        print("")
        print("")
        print(c.name)

        materials = {}

        context = blueprint.MaterialContext()

        for bp in c.contents:

            if bp.isBPO():
                continue

            context.add_blueprint(bp)

        context.cook()

        def getTypeName(typeID):
            cursor = database.cursor()
            cursor.execute("SELECT typeName "
                           "FROM invTypes "
                           "WHERE typeID = ?",
                           [typeID])

            (typeName, ) = cursor.fetchone()
            return typeName

        required = { getTypeName(typeID): quantity
                     for typeID, quantity in context.materials.items() }

        surplus = { getTypeName(typeID): quantity
                    for typeID, quantity in context.surplus.items() }
            
        print("")
        print("Materials Needed:")
        
        for typeName, quantity in required.items():
            print("{:<16,}\t{}".format(quantity, typeName))
   
        print("")
        print("Materials left over after construction:")
        
        for typeName, quantity in surplus.items():
            print("{:<16,}\t{}".format(quantity, typeName))


if __name__ == "__main__":

    args = sys.argv[1:]

    configfile = args[0] if args else "userconfig.xml" 
    main(configfile)
