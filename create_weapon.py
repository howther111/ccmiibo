import pandas as pd
import random
import CreatePetName

class Weapon:
    weapon_name = ""
    element = ""
    attack_base = 0
    attack_level = 0
    attack_random = 0
    type = ""
    critical = 12
    target = ""
    min_range = 0
    max_range = 0
    def createWeapon(self, enemy_level=0, weapon_name="", element="", attack_base=0, attack_level=0,
                     attack_random=0, attack=0, weapon_type="", critical=12, target="", min_range=0, max_range=0):
        self.weapon_name = weapon_name
        self.element = element
        self.attack_base = attack_base
        self.attack_level = attack_level
        self.attack_random = attack_random
        self.attack = attack
        self.weapon_type = weapon_type
        self.critical = critical
        self.target = target
        self.min_range = min_range
        self.max_range = max_range

    def setEnemy_level(self, enemy_level):
        self.enemy_level = int(enemy_level)

    def setWeapon_name(self, weapon_name):
        self.weapon_name = str(weapon_name)

    def setElement(self, element):
        self.element = str(element)

    def setAttack_base(self, attack_base):
        self.attack_base = int(attack_base)

    def setAttack_level(self, attack_level):
        self.attack_level = int(attack_level)

    def setAttack_random(self, attack_random):
        self.attack_random = int(attack_random)

    def setAttack(self):
        randomattack = self.enemy_level * self.attack_random
        self.attack = (self.attack_base + (self.enemy_level * self.attack_level)
                       + random.randint(0, randomattack))

    def setWeapon_type(self, weapon_type):
        self.weapon_type = str(weapon_type)

    def setCritical(self, critical):
        self.critical = int(critical)

    def setTarget(self, target):
        self.target = str(target)

    def setMin_range(self, min_range):
        self.min_range = int(min_range)

    def setMax_range(self, max_range):
        self.max_range = int(max_range)

    def print_data(self):
        print("enemy_level=" + str(self.enemy_level))
        print("weapon_name=" + self.weapon_name)
        print("element=" + self.element)
        print("attack_base=" + str(self.attack_base))
        print("attack_level=" + str(self.attack_level))
        print("attack_random=" + str(self.attack_random))
        print("attack=" + str(self.attack))
        print("weapon_type=" + str(self.weapon_type))
        print("critical=" + str(self.critical))
        print("target=" + self.target)
        print("min_range=" + str(self.min_range))
        print("max_range=" + str(self.max_range))

def create_weapon(level=3):
    df_weapon = pd.read_csv('random_weapon.csv', header=0)
    # <class 'pandas.core.frame.DataFrame'>

    print(df_weapon)

    df_element = pd.read_csv('random_element.csv', header=0)
    # <class 'pandas.core.frame.DataFrame'>

    print(df_element)

    weapon_row = df_weapon.sample(n=1)
    random_element = df_element.sample(n=1)
    print(weapon_row)
    new_weapon = Weapon()

    new_weapon.setEnemy_level(enemy_level)
    if str(weapon_row["element"].values[0]) == "乱":
        basename = random_element["name"].values[0]
        randomname = CreatePetName.CreatePetName()
        weaponname = weapon_row["weapon_name"].values[0].replace("乱", randomname)
        new_weapon.setWeapon_name(basename + weaponname)
        new_weapon.setElement(random_element["element"].values[0])
    else:
        new_weapon.setWeapon_name(weapon_row["weapon_name"].values[0])
        new_weapon.setElement(weapon_row["element"].values[0])

    new_weapon.setAttack_base(weapon_row["attack_base"].values[0])
    new_weapon.setAttack_level(weapon_row["attack_level"].values[0])
    new_weapon.setAttack_random(weapon_row["attack_random"].values[0])
    new_weapon.setAttack()
    new_weapon.setWeapon_type(weapon_row["weapon_type"].values[0])
    new_weapon.setCritical(weapon_row["critical"].values[0])
    new_weapon.setTarget(weapon_row["target"].values[0])
    new_weapon.setMin_range(weapon_row["min_range"].values[0])
    new_weapon.setMax_range(weapon_row["max_range"].values[0])
    #new_weapon.print_data()

    return new_weapon

enemy_level = 3
weapon = create_weapon(level=enemy_level)
weapon.print_data()
