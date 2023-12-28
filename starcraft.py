import random, json, math, time
from itertools import accumulate
from enum import Enum
import gettext
from termcolor import cprint, colored

#prepare:
#set path=%path%;c:\users\antlas\appdata\roaming\python\python311\Scripts\
#pybabel extract -o lang/messages.pot starcraft.py
#--first time: pybabel init -l ru -i lang/messages.pot -d lang/
#pybabel update -i lang/messages.pot -l ru -d lang/
#pybabel compile -d lang/

# initialization
lang_ru = gettext.translation('messages', localedir='lang', languages=['ru'])
# set current locale to ru
lang_ru.install()

            
#A text-based RPG game based on Minecraft

def one_in(x):
    "Returns True with a probability of 1/x, otherwise returns False"
    return x <= 1 or random.randint(1, x) == 1

def x_in_y(x, y):
    "Returns True with a probability of x/y, otherwise returns False"
    return random.uniform(0, y) < x
    
def binomial(num, x, y=100):
    if x == 1 and isinstance(y, int):
        return sum(1 for i in range(num) if one_in(y))
    else:
        return sum(1 for i in range(num) if x_in_y(x, y))

def round_stochastic(value):
    """Randomly rounds a number up or down, based on its decimal part
    For example, 5.3 has a 70% chance to be rounded to 5, 30% chance to be rounded to 6
    And 2.8 has an 80% chance to be rounded to 3, 20% chance to be rounded to 2"""
    low = math.floor(value)
    high = math.ceil(value)
    if value < 0:
        if random.random() < high - value:
            return low
        return high
    else:
        if random.random() < value - low:
            return high
        return low 

def choice_input(*choices, return_text=False):
    for index, choice in enumerate(choices):
        print(f"{index + 1}. {choice}")
    while True:
        try:
            choice = int(input(">> "))
        except ValueError:
            continue
        else:
            if 1 <= choice <= len(choices):
                return choices[choice - 1] if return_text else choice

def yes_no(message):
    m = input(message + _(" (Y/N) "))
    return len(m) > 0 and m[0].lower() == _("y")

class JSONDict(dict):
    
    def __init__(self, d={}):
        super().__init__(d)
        for key in self:
            if type(self[key]) == dict:
                self[key] = self.__class__(self[key])
    
    def __missing__(self, key):
        raise JSONError(f"missing required field {key!r}", self)
    
    def gettype(self, key, typ):
        value = self[key]
        if typ == float:
            typ = (float, int)
        if isinstance(value, typ):
            return value
        else:
            raise JSONError(f"field {key!r} expected value of type {typ.__name__!r}, but got {value.__class__.__name__!r}", self)
        
    def gettype_or_default(self, key, typ, default=None):
        if key not in self:
            return default
        return self.gettype(key, typ)
        
class JSONError(Exception):
        
    def __init__(self, message, context=None):
        msg = message
        if context:
            msg += f"\n\nJSON Context: \n{json.dumps(context)}"
        super().__init__(msg)
        
def json_dict(func):
    if type(func) == staticmethod:
         func = func.__get__(object)
    def wrapper(d, *args, **kwargs):
        if type(d) != JSONDict:
             d = JSONDict(d)
        return func(d, *args, **kwargs)
    return wrapper
    
class MobBehaviorType(Enum):
    passive = 0 #Passive; won't attack even if attacked
    neutral = 1 #Neutral; will become hostile if attacked
    hostile = 2 #Hostile; 50% chance to attack immediately when encountered

class WeightedList:
    
    def __init__(self):
        self.choices = []
        self.weights = []
        self.cumulative_weights = None
        
    def add(self, value, weight):
        if weight > 0:
            self.choices.append(value)
            self.weights.append(weight)
            self.cumulative_weights = None 
    
    def clear(self):
        self.choices.clear()
        self.weights.clear()
        self.cumulative_weights = None 
        
    def pick(self):
        if len(self.choices) == 0:
            raise IndexError("cannot pick from an empty weighted list")
        if not self.cumulative_weights:
            self.cumulative_weights = list(accumulate(self.weights))
        return random.choices(self.choices, cum_weights=self.cumulative_weights)[0]

mobs_dict = json.load(open("mobs.json"))

class MobType:
    
    def __init__(self, name, weight, max_hp, behavior: MobBehaviorType, death_drops, attack_strength, spawns_naturally):
        self.name = name
        self.weight = weight
        self.hp = max_hp
        self.behavior = behavior
        self.death_drops = death_drops
        self.attack_strength = attack_strength
        self.spawns_naturally = True
    
    @json_dict  
    @staticmethod
    def from_dict(d):
        name = d.gettype("name", str)
        HP = d.gettype("HP", int)
        b = d.gettype("behavior", str)
        spawns_naturally = d.gettype_or_default("spawns_naturally", bool, True) 
        weight = d.gettype("weight", int) if spawns_naturally else 0
        if b == "passive":
            behavior = MobBehaviorType.passive
        elif b == "neutral":
            behavior = MobBehaviorType.neutral
        elif b == "hostile":
            behavior = MobBehaviorType.hostile
        else:
            raise JSONError(f"Invalid behavior type {b!r}", d)
        attack_strength = d.gettype_or_default("attack_strength", float)
        if attack_strength is None and b != "passive":
            raise JSONError("Non-passive mobs require an attack strength", d)
        death_drops = d.gettype_or_default("death_drops", list, [])
        for drop in death_drops:
            drop = JSONDict(drop)
            if not isinstance(drop, dict):
                raise JSONError("Each entry in death_drops must be a dict", drop)
            item = drop.gettype("item", (str, list))    
            if "chance" in drop and (not isinstance(drop["chance"], list) or len(drop["chance"]) != 2):
                raise JSONError("chance must be a 2-item list", drop) 
            if "quantity" in drop and not (isinstance(drop["quantity"], int) or (isinstance(drop["quantity"], list) and len(drop["quantity"]) == 2)):
                raise JSONError("quantity muat be an int or a 2-item list", drop)   
        return MobType(name, weight, HP, behavior, death_drops, attack_strength, spawns_naturally)

mob_types = {}

for mob_dict in mobs_dict:
    name = mob_dict["name"]
    mob_types[name] = MobType.from_dict(mob_dict)   

#passive_mob_types = list(filter(lambda typ: mob_types[typ].behavior == MobBehaviorType.passive, mob_types))
#night_mob_types = list(filter(lambda typ: mob_types[typ].night_mob, mob_types))
day_mob_types = WeightedList()
#night_mob_types = WeightedList()
for typ in mob_types:
    mob_type = mob_types[typ]
    if mob_type.spawns_naturally:
        #if mob_type.night_mob:
        #   night_mob_types.add(typ, mob_type.weight)
        #else:
        day_mob_types.add(typ, mob_type.weight)

class Mob:
    
    def __init__(self, name, HP, behavior: MobBehaviorType, death_drops, attack_strength):
        self.name = name
        self.HP = HP
        self.behavior = behavior
        self.death_drops = death_drops
        self.attack_strength = attack_strength
        
    @staticmethod
    def new_mob(typ: str):
        typ = mob_types[typ]
        return Mob(typ.name, typ.hp, typ.behavior, typ.death_drops, typ.attack_strength)
    
    def damage(self, amount, player):
        self.HP -= amount
        if self.HP <= 0:
            print(_("The {0} is dead!").format(self.name.lower()))
            self.on_death(player)
            
    def on_death(self, player):
        if self.death_drops:
            got = {}
            for drop in self.death_drops:
                item = drop["item"]
                if isinstance(item, list):
                    item = random.choice(item)
                q = drop.get("quantity", 1)
                x, y = drop.get("chance", [1, 1])
                assert isinstance(q, (list, int))   
                if isinstance(q, list):
                    amount = random.randint(*q)
                elif isinstance(q, int):
                    amount = q
                if amount > 0 and x_in_y(x, y):
                    if item == "EXP":
                        player.gain_exp(amount)
                    else:
                        got[item] = amount
            if got:
                print("You got: ")
                for item in got:
                    print(f"{got[item]}x {item}")
                    player.add_item(item, got[item])

class ToolData:
    
    def __init__(self, damage, durability, attack_speed, mining_mult):
        self.damage = damage
        self.durability = durability
        self.attack_speed = attack_speed
        self.mining_mult = mining_mult
    
    @json_dict
    @staticmethod   
    def from_dict(d):
        damage = d.gettype_or_default("damage", int, 1)
        durability = d.gettype("durability", int)
        attack_speed = d.gettype_or_default("attack_speed", (int, float), 4)
        mining_mult = d.gettype_or_default("mining_mult", (int, float), 1)
        return ToolData(damage, durability, attack_speed, mining_mult)  

class Recipe:
    
    def __init__(self, quantity, components, tool_data=None):
        self.quantity = quantity
        self.components = components
        self.tool_data = tool_data
    
    @json_dict  
    @staticmethod
    def from_dict(d):
        quantity = d.gettype_or_default("quantity", int, 1)
        components = d.gettype("components", list)
        tool_data = d.gettype_or_default("tool_data", JSONDict)
        if tool_data:
            tool_data = ToolData.from_dict(tool_data)
        return Recipe(quantity, components, tool_data)
        
r = json.load(open("recipes.json"))
recipes = {}
for name in r:
    recipe = r[name]
    recipes[name] = Recipe.from_dict(recipe)

#foods = json.load(open("foods.json"))
            
class Time:
    
    def __init__(self):
        self.mins = 0
        self.secs = 0
        
    #def is_night(self):
    #   return self.mins >= 20
    
    def advance(self, secs):
        #was_night = self.is_night()
        #last_mins = self.mins
        self.secs += secs
        while self.secs >= 60:
            self.mins += 1
            self.secs -= 60
        self.mins %= 40
        #is_night = self.is_night()
        #if was_night ^ is_night:
        #   if is_night:
        #       cprint("It is now nighttime", "blue")
        #   else:
        #       cprint("It is now daytime", "blue")
        #elif last_mins < 18 and self.mins >= 18:
        #   cprint("The sun begins to set", "blue")
        #elif last_mins < 38 and self.mins >= 38:
        #   cprint("The sun begins to come up", "blue")
            
class StatusEffect:
    
    def __init__(self, level, duration):
        self.level = level
        self.duration = duration

def get_exp_required_for_level(level):
    assert level >= 0
    if level <= 16:
        return level ** 2 + 6 * level
    if level < 32:
        return round(2.5 * level**2 - 40.5 * level + 360)
    return round(4.5 * level**2 - 160.5 * level + 2220)

class Player:
    
    def __init__(self):
        self.HP = 20
        #self.hunger = 20
        #self.food_exhaustion = 0
        self.saturation = 5
        self.inventory = {}
        self.tools = []
        self.curr_weapon = None
        self.EXP = 0
        self.level = 0
        self.time = Time()
        self.ticks = 0
        self.status_effects = {}
        
    def get_effect_level(self, name):
        if name not in self.status_effects:
            return 0
        return self.status_effects[name].level
        
    def apply_status_effect(self, name, level, duration):
        if name == "Instant Damage":
            self.damage(3 * 2**level, death_reason="Killed by magic", physical=False)
            return
        if name == "Instant Health":
            self.heal(2 * 2**level)
            return
        cur_level = self.get_effect_level(name)
        if cur_level == 0:
            self.status_effects[name] = StatusEffect(level, duration)
        elif level > cur_level:
            effect_obj = self.status_effects[name]
            effect_obj.level = level
            effect_obj.duration = duration
        
    def advance_time(self, secs):
        self.time.advance(secs)
        for effect in list(self.status_effects.keys()): #Convert to list to save a snapshot of the keys so we can avoid RuntimeError due to changing the size during iteration
            self.status_effects[effect].duration -= secs
            if self.status_effects[effect] <= 0:
                del self.status_effects[effect]
                
    def tick_status_effect(self, name):
        if name not in self.status_effects:
            return
        effect = self.status_effects[name]
        level = effect.level
        #if name == "Hunger":
        #   self.mod_food_exhaustion(0.05 * level)
        if name == "Poison":
            level = (level - 1) % 32 + 1
            rate = max(1, 25 // 2**level)
            amount = min(self.HP - 1, round_stochastic(20 / rate)) #Poison reduces us to 1 HP but doesn't kill us
            self.damage(amount, physical=False)
        
    def damage(self, amount, death_reason=None, physical=True):
        if amount <= 0:
            return
        cprint(_("You take {0} damage!").format(amount), "red")
        self.HP -= amount
        #if physical:
        #   self.mod_food_exhaustion(0.1)
        if self.HP <= 0:
            self.die(death_reason)
        self.print_health()
        
    def gain_exp(self, amount):
        amount = round_stochastic(amount)
        if amount <= 0:
            return
        self.EXP += amount
        print(_("+{0} EXP").format(amount))
        old_level = self.level
        while get_exp_required_for_level(self.level) <= self.EXP:
            self.level += 1
        if self.level > old_level:
            cprint(_("You have reached level {0}!").format(self.level), "green")
        print(_("Current EXP: {0}/{1}").format(self.EXP,get_exp_required_for_level(self.level)))
        
    def die(self, death_reason=None):
        print(_("You died!"))
        if death_reason:
            print(death_reason)
        print("\n"+_("Score: {0}").format(self.EXP))
        exit()
        
    def print_health(self):
        print(_("HP: {0}/20").format(self.HP))
        
    def heal(self, amount):
        if amount <= 0:
            return False
        old_hp = self.HP
        self.HP = min(self.HP + amount, 20)
        healed_by = self.HP - old_hp
        if healed_by > 0:
            cprint(_("You are healed by {0} HP.").format(healed_by), "green")
            self.print_health()
            return True
        return False
     
    def tick(self, is_battle):
        self.ticks += 1
        if (self.HP < 20) and (self.ticks % 4 == 0) and (is_battle == False):
            self.heal(1)
        self.advance_time(0.5)
    
    def add_item(self, item, amount=1):
        if item in self.inventory:
            self.inventory[item] += amount
        else:
            self.inventory[item] = amount
            
    def add_tool(self, tool):
        self.tools.append(tool)
            
    def remove_item(self, item, amount):
        if amount <= 0:
            return
        if item not in self.inventory or amount > self.inventory[item]:
            raise ValueError("Tried to remove more of item than available in inventory")
        self.inventory[item] -= amount
        if self.inventory[item] <= 0:
            del self.inventory[item]
            
    def armed(self):
        return self.curr_weapon is not None
        
    def attack_damage(self):
        return self.curr_weapon.damage if self.armed() else 1
        
    def attack_speed(self):
        return self.curr_weapon.attack_speed if self.armed() else 4
        
    def has_item(self, item, amount=1):
        if item not in self.inventory:
            return False
        return self.inventory[item] >= amount
        
    def has_any_item(self, names):
        return any(name in self.inventory for name in names)
        
    def has_tool(self, tool_name):
        return any(tool.name == tool_name for tool in self.tools)
    
    def has_any_tool(self, tool_names):
        l1 = set(tool_names)
        l2 = set(tool.name for tool in self.tools)
        return not l1.isdisjoint(l2)
        
    def can_make_recipe(self, recipe):
        for component in recipe.components:
            name, amount = component
            if not self.has_item(name, amount):
                return False
        return True 
            
    def decrement_tool_durability(self):
        tool = self.curr_weapon
        if tool:
            tool.durability -= 1
            if tool.durability < 0:
                cprint(_("Your {0} is destroyed!").format(tool.name), "red")
                self.tools.remove(tool)
                self.curr_weapon = None
            else:
                print(_("Durability: {0}").format(durability_message(tool.durability, tool.max_durability)))
            
    def switch_weapon_menu(self):
        if len(self.tools) > 0:
            options = [] 
            for tool in self.tools:
                options.append(_("{0} - Durability {1}").format(tool.name,durability_message(tool.durability, tool.max_durability)))
            options.append(_("Unarmed"))
            print(_("Which weapon would you like to switch to?"))
            choice = choice_input(*options)
            if choice == len(self.tools) + 1:
                print(_("You decide to go unarmed"))
                self.curr_weapon = None
            else:
                weapon = self.tools[choice - 1]
                print(_("You switch to your {0}").format(weapon.name))
                self.curr_weapon = weapon
            
class Tool:
    
    def __init__(self, name, damage, durability, mining_mult, attack_speed):
        self.name = name
        self.damage = damage
        self.durability = durability
        self.max_durability = durability
        self.mining_mult = mining_mult
        self.attack_speed = attack_speed
                
def durability_message(durability, max_durability):
    durability_msg = f"{durability}/{max_durability}"
    if durability <= max_durability // 4:
        color = "red"
    elif durability <= max_durability // 2:
        color = "yellow"
    else:
        color = "green"
    return colored(durability_msg, color)
    
def random_battle(player, action_verb):
    _ = lang_ru.gettext
    #if night_mob:
    #   choices = night_mob_types
    #else:
    choices = day_mob_types
    mob = Mob.new_mob(choices.pick())
    #mob = Mob.new_mob("Enderman")
    if mob.name == "Baby Zombie" and one_in(20):
        mob = Mob.new_mob("Chicken Jockey")
    mob_name = mob.name.lower()
    a_an = "an" if mob_name[0] in "aeiou" else "a"
    p1 = _("You found")
    p2 = _("while")
    print(p1 + " {0} {1} ".format(a_an,mob_name) + p2 + " {0}{1}".format(action_verb,'!' if mob.behavior == MobBehaviorType.hostile else '.'))
    if mob.behavior == MobBehaviorType.hostile and not mob_name.endswith("creeper") and one_in(2):
        cprint(_("The {0} attacks you!").format(mob_name), "red")
        player.damage(mob.attack_strength)
    if mob.name == "Chicken" and one_in(15):
        print("You got 1x Egg")
        player.add_item("Egg")
    creeper_turn = 0
    choice = choice_input(_("Attack"), _("Flee") if mob.behavior == MobBehaviorType.hostile else _("Ignore"))
    if choice == 1:
        if len(player.tools) > 0 and yes_no(_("Would you like to switch weapons?")):
            player.switch_weapon_menu()
        run = 0
        while True:
            if run > 0:
                run -= 1
                if run == 0:
                    print(_("The {0} stops running.").format(mob_name))
            #player.mod_food_exhaustion(0.1)
            is_enderman = mob.name == "Enderman"
            miss_chance = 5 if is_enderman else 10
            if one_in(miss_chance):
                if is_enderman:
                    print(_("You swing at the {0} but it teleports away.").format(mob_name))
                else:
                    print(_("You swing at the {0} but miss.").format(mob_name))
            elif run > 0 and not one_in(3) and x_in_y(1, player.attack_speed() + 1):
                flee_miss_messages = [
                    _("You try to attack the {} while it was fleeing, and miss."),
                    _("You swing at the {}, but miss as it was running away too fast."),
                    _("The {} was fleeing too quickly, you miss!"),
                    _("You swing at the {}, and miss narrowly."),
                    _("You try to attack the {} while it was running away, and miss.")
                ]
                print(random.choice(flee_miss_messages).format(mob_name))
            else:           
                damage = player.attack_damage()
                is_critical = one_in(10)
                base_damage = damage
                if is_critical:
                    damage = int(damage * 1.5)
                    is_critical = is_critical and damage > base_damage
                print(_("You attack the {0}.{1}").format(mob_name,_(' Critical!') if is_critical else '')) #TODO: Vary this message based on wielded weapon
                player.decrement_tool_durability()
                mob.damage(damage, player)
                if mob.HP <= 0:
                    break
                if mob.behavior == MobBehaviorType.passive:
                    if not one_in(damage + 1) and run == 0:
                        print(_("The {} starts running away.").format(mob_name))
                        run += random.randint(3, 5)
            attack_speed = player.attack_speed() #Attack speed controls the chance of being attacked by a mob when we attack
            #time.sleep(random.uniform(0.75, 1.25) / attack_speed)
            if mob_name.endswith("creeper"):
                creeper_turn += 1
                if creeper_turn > 2 and not one_in(creeper_turn): #Increasing chance to explode after the first 2 turns
                    damage = max(random.randint(1, mob.attack_strength) for _ in range(3)) #attack_strength defines explosion power for creepers
                    print(_("The creeper explodes!"))
                    player.damage(damage, _("Killed by a creeper's explosion"))
                    explosion_power = 6 if mob.name == "Charged Creeper" else 3
                    if action_verb == _("mining"):
                        minables.add(_("Stone"), 3000) #Explosions drop the block instead of the item
                        minables.add(_("Coal Ore"), 124)
                        minables.add(_("Iron Ore"), 72)
                        minables.add(_("Lapis Lazuli Ore"), 3)
                        minables.add(_("Gold Ore"), 7)
                        minables.add(_("Diamond Ore"), 3)
                        num = int((explosion_power * random.uniform(0.75, 1.25)) ** 2) + 1
                        found = {}
                        for _ in range(num):
                            if one_in(explosion_power):
                                s = minables.pick()
                                if s in found:
                                    found[s] += 1
                                else:
                                    found[s] = 1
                        if len(found) > 0:
                            print(_("You got the following items from the explosion:"))
                            for item in found:
                                print(f"{found[item]}x {item}")
                                player.add_item(item, found[item])
                    else:
                        grass = random.randint(explosion_power // 3, explosion_power) + 1
                        dirt = int((explosion_power * random.uniform(0.75, 1.25)) ** 2) + 1
                        grass = binomial(grass, 1, explosion_power)
                        dirt = binomial(dirt, 1, explosion_power)
                        player.add_item(_("Dirt"), dirt)
                        player.add_item(_("Grass"), grass)
                        if grass > 0:
                            if dirt > 0:
                                print(_("You got {0}x Grass and {1}x Dirt from the explosion").format(grass,dirt))
                            else:
                                print(_("You got {0}x Grass from the explosion").format(grass))
                        elif dirt > 0:
                            print(_("You got {0}x Dirt from the explosion").format(dirt))
                    break
                else:
                    print(_("The creeper flashes..."))
            elif mob.behavior != MobBehaviorType.passive and x_in_y(1, attack_speed) and not one_in(8): #I use x_in_y instead of one_in because x_in_y works with floats
                print(_("The {0} attacks you!").format(mob_name))
                player.damage(round_stochastic(mob.attack_strength))
            player.tick(True)
            choice = choice_input(_("Attack"), _("Ignore") if mob.behavior == MobBehaviorType.passive else _("Flee"))
            if choice == 2:
                return
                
splashes = open("splashes.txt",encoding="utf-8").read().splitlines()

print("""
   _____ _______       _____   _____ _____            ______ _______ 
  / ____|__   __|/\   |  __ \ / ____|  __ \     /\   |  ____|__   __|
 | (___    | |  /  \  | |__) | |    | |__) |   /  \  | |__     | |   
  \___ \   | | / /\ \ |  _  /| |    |  _  /   / /\ \ |  __|    | |   
  ____) |  | |/ ____ \| | \ \| |____| | \ \  / ____ \| |       | |   
 |_____/   |_/_/    \_\_|  \_\\______|_|  \_\/_/    \_\_|       |_|   
""")
print()
print()
cprint(random.choice(splashes), "yellow", attrs=["bold"])
print()
choice = choice_input(_("Play"), _("Quit"))
if choice == 2:
    exit()
    
player = Player()

while True:
    player.tick(False)
    #if player.time.is_night():
    #   print("It is currently nighttime")
    player.print_health()
    #player.print_hunger()
    if player.curr_weapon:
        weapon = player.curr_weapon
        print(_("Current weapon: {0} - Durability {1}").format(player.curr_weapon.name,durability_message(weapon.durability, weapon.max_durability)))
    options = [_("Explore"), _("Inventory"), _("Craft")]
    if len(player.tools) > 0:
        options.append(_("Switch Weapon"))
    #foods_in_inv = list(filter(lambda item: item in foods, player.inventory))
    #if foods_in_inv:
    #   options.append("Eat")
    has_pickaxe = any("Pickaxe" in tool.name for tool in player.tools)
    if has_pickaxe:
        options.append(_("Mine"))
    choice = choice_input(*options, return_text=True)
    if choice == _("Explore"):
        print(_("You explore for a while."))
        time_explore = random.randint(15, 20)
        #time.sleep(time_explore / 20)
        #player.mod_food_exhaustion(0.001 * time_explore)
        player.advance_time(time_explore)
        mob_chance = 3 #daytime - 3, night - 8
        if one_in(mob_chance):
            random_battle(player,_("exploring"))
        elif x_in_y(3, 5):
            explore_finds = [(_("Grass"), 8), (_("Dirt"), 1), (_("Wood"), 4)]
            choices = [val[0] for val in explore_finds]
            weights = [val[1] for val in explore_finds]
            found = random.choices(choices, weights=weights)[0]
            print(_("You found 1x {}").format(found))
            player.add_item(found)
    elif choice == _("Inventory"):
        if len(player.inventory) == 0:
            print(_("There is nothing in your inventory"))
        else:
            print(_("Your inventory:"))
            for item in player.inventory:
                print(f"{player.inventory[item]}x {item}")
            print(_("Your tools:"))
            for index, tool in enumerate(player.tools):
                print(_("{0}. {1} - Durability {2}/{3}").format(index+1,tool.name,tool.durability,tool.max_durability))
    elif choice == _("Craft"):
        craftable = []
        for recipe in recipes:
            info = recipes[recipe]
            if player.can_make_recipe(info):
                craftable.append((recipe, recipes[recipe]))
        if len(craftable) == 0:
            print(_("There are no items that you have the components to craft"))
        else:
            print(_("Items you can craft:"))
            for item in craftable:
                name, info = item
                quantity = info.quantity
                string = f"{quantity}x {name} |  " + _("Components: ")
                components = info.components
                string += ", ".join(f"{c[1]}x {c[0]}" for c in components)
                print(string)
                print()     
            print(_("What would you like to craft?"))
            item_name = input()
            item = next((v for v in craftable if v[0] == item_name), None)
            if item is not None:
                name, info = item
                components = info.components
                quantity = info.quantity
                for component in components:
                    player.remove_item(*component)
                if info.tool_data is not None:
                    tool_data = info.tool_data
                    damage = tool_data.damage
                    durability = tool_data.durability
                    mining_mult = tool_data.mining_mult
                    attack_speed = tool_data.attack_speed
                    player.add_tool(Tool(name, damage, durability, mining_mult, attack_speed))
                else:
                    player.add_item(name, quantity)
                print(_("You have crafted {0}x {1}").format(quantity,name))
            else:
                print(_("Invalid item"))
    elif choice == _("Switch Weapon"):
        player.switch_weapon_menu()
    elif choice == _("Mine"):
        if player.curr_weapon and "Pickaxe" in player.curr_weapon.name:
            tiers = ["Wooden Pickaxe", "Stone Pickaxe", "Iron Pickaxe"]
            tier_num = tiers.index(player.curr_weapon.name) + 1
            minables = WeightedList()
            minables.add(_("Stone"), 1500)
            minables.add(_("Coal"), 124)
            if tier_num > 1:
                minables.add(_("Raw Iron"), 72)
                minables.add(_("Lapis Lazuli"), 3)
                if tier_num > 2:
                    minables.add(_("Raw Gold"), 7)
                    minables.add(_("Diamond"), 3)
            found = minables.pick()
            if found == _("Coal"):
                exp_gain = random.randint(0, 2)
            elif found == _("Lapis Lazuli"):
                exp_gain = random.randint(2, 5)
            elif found == _("Diamond"):
                exp_gain = random.randint(3, 7)
            else:
                exp_gain = 0
            if found == _("Lapis Lazuli"):
                quantity = random.randint(4, 9)
            else:
                quantity = 1
            print(_("Mining..."))
            #time.sleep(random.uniform(0.75, 1.5))
            mine_mult = player.curr_weapon.mining_mult
            mob_chance = 10# day chance 10, night 15
            mob_chance *= math.sqrt(mine_mult)
            mob_chance = round(mob_chance)
            if found == _("Stone") and one_in(3):
                print(_("You didn't find much of value"))
                player.advance_time(3)
            else:
                print(_("You found")+f"{quantity}x {found}")
                player.gain_exp(exp_gain)
                player.add_item(found, quantity)
                #player.mod_food_exhaustion(0.005)
                if found == _("Stone"):
                    base_mine_time = 1.5
                else:
                    base_mine_time = 3
                mine_time = round(base_mine_time / mining_mult, 2)
                player.advance_time(mine_time)
                player.decrement_tool_durability()
            if one_in(mob_chance):
                random_battle(player, True, _("mining"))
        else:
            print(_("You need to switch to your pickaxe to mine"))