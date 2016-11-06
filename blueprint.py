#
#
#

import math
import database as db



global cfgtree

def initialize(configtree):
        
    global cfgtree
    cfgtree = configtree


def _getTypeName(typeID):
    cursor = db.cursor()
    cursor.execute("SELECT typeName "
                   "FROM invTypes "
                   "WHERE typeID = ?",
                   [typeID])
    
    (typeName, ) = cursor.fetchone()
    return typeName


def _getBaseTime(typeID):
    
    cursor = db.cursor()
    cursor.execute("SELECT time "
                   "FROM industryActivity "
                   "WHERE typeID = ? "
                   "AND activityID = 1",
                   [typeID])

    (time, ) = cursor.fetchone()
    return time

def _getQuantityPerRun(typeID):
    
    cursor = db.cursor()
    cursor.execute("SELECT quantity "
                   "FROM industryActivityProducts "
                   "WHERE typeID = ?",
                   [typeID])

    (quantity, ) = cursor.fetchone()
    return quantity
    

def _getBaseMaterials(typeID):

    cursor = db.cursor()
    cursor.execute("SELECT materialTypeID as typeID, quantity "
                   "FROM industryActivityMaterials " +
                   "WHERE activityID = 1 AND typeID = ?", 
                   [typeID])

    return dict(cursor.fetchall())


def _getTotalMaterialsFor(typeID, quantity, me):

    # Calculate the number of runs needed to meet the required quantity.
    cursor = db.cursor()
    cursor.execute("SELECT productTypeID, quantity "
                   "FROM industryActivityProducts "
                   "WHERE activityID = 1 "
                   "AND typeID = ?", 
                   [typeID])

    (productTypeID, productQuantity) = cursor.fetchone()
    
    runs = quantity
    
    global cfgtree
    stationFactor = float(cfgtree.find('.//stationProductionEfficiency/default').text)
        
    materials = {}

    for typeID, quantity in _getBaseMaterials(typeID).items():
        if quantity == 1:
            materials[typeID] = runs 
            continue

        factor = float(100 - me) / 100
        materials[typeID] = int(math.ceil(runs * factor * stationFactor * quantity))

    return materials


def _getBlueprintTypeID(typeID):
        
    cursor = db.cursor()
    cursor.execute("SELECT typeID "
                   "FROM industryActivityProducts "
                   "WHERE activityID = 1 AND productTypeID = ?",
                   [typeID])
        
    res = cursor.fetchone()
    
    if res == None:
        return None

    (typeID, ) = res
    return typeID


class Blueprint:

    def __init__(self, elm):


        for attr in elm.attrib.keys():
            setattr(self, attr, elm.get(attr))

        integers = ['timeEfficiency', 'materialEfficiency', 'runs']

        for attr in integers:
            setattr(self, attr, int(getattr(self, attr)))
    
        
    def isBPO(self):
        return self.runs == -1


    def __str__(self):
        return ("{} "
                "["
                "ME: {}, "
                "PE: {}, "
                "runs: {}"
                "]").format(self.typeName, 
                            self.materialEfficiency,
                            self.timeEfficiency,
                            self.runs if self.runs is not -1 else 'BPO')


class MaterialContext:

    def __init__(self):
     
        self.materials = Materials()
        self.surplus = Materials()


    def add_blueprint(self, bp):

        print("Adding blueprint:")
        print(bp)

        self.materials += _getTotalMaterialsFor(bp.typeID, bp.runs, bp.materialEfficiency)


    def _get_submaterials(self):

        submaterials = set([])
       
        types = set(self.materials.keys())

        while types:
            
            typeID = types.pop()

            blueprintTypeID = _getBlueprintTypeID(typeID)

            if blueprintTypeID is None:
                continue


            materials = _getBaseMaterials(blueprintTypeID)
            materials = set(materials.keys())

            submaterials.update(materials)
            types.update(materials)

        return submaterials


    def cook(self):
        
        def isFinalMaterial(typeID):
            return _getBlueprintTypeID(typeID) is None

        if all([isFinalMaterial(typeID) for typeID in self.materials]):
            print("Done!")
            return

        submaterials = self._get_submaterials()

        # Replace a non-final material with it's input. Register surplus. 
        pending = set([typeID for typeID in self.materials 
                       if not isFinalMaterial(typeID) 
                       and typeID not in submaterials])

        typeID = pending.pop()

        print('Cooking: {} [{}]'.format(_getTypeName(typeID), typeID))

        blueprintID = _getBlueprintTypeID(typeID)



        quantity = self.materials[typeID]
        del self.materials[typeID]

        runs = int(math.ceil(float(quantity) / _getQuantityPerRun(blueprintID)))

        print('\t{} units ({} runs)'.format(quantity, runs))

        # Do we have any surplus:
        
        surplus = _getQuantityPerRun(blueprintID) * runs - quantity
        if surplus:
            print('Surplus: {} {}'.format(_getTypeName(typeID), surplus))

            self.surplus += { typeID: surplus }

        
        self.materials += _getTotalMaterialsFor(blueprintID, runs, 10) 
 
        self.cook()



class Materials(dict):
    
    def __add__(self, other):
        
        for key, quantity in other.items():
            
            if key not in self:
                self[key] = 0

            self[key] += quantity

        return self
        


