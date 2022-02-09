import random, json
from enum import Enum

#A text-based RPG game based on Minecraft

def one_in(x):
	return x <= 1 or random.randint(1, x) == 1

def choice_input(*choices):
	for index, choice in enumerate(choices):
		print(f"{index + 1}. {choice}")
	while True:
		try:
			choice = int(input(">> "))
		except ValueError:
			continue
		else:
			if 1 <= choice <= len(choices):
				return choice
				
class MobBehaviorType(Enum):
	passive = 0 #Passive; won't attack even if attacked
	neutral = 1 #Neutral; will become hostile if attacked
	hostile = 2 #Hostile; will always attack

mobs_dict = json.load(open("mobs.json"))

class MobType:
	
	def __init__(self, name, max_hp, behavior: MobBehaviorType, death_drops):
		self.name = name
		self.hp = max_hp
		self.behavior = behavior
		self.death_drops = death_drops
		
	@staticmethod
	def from_dict(d):
		name = d["name"]
		HP = d["HP"]
		b = d["behavior"]
		if b == "passive":
			behavior = MobBehaviorType.passive
		elif b == "neutral":
			behavior = MobBehaviorType.neutral
		elif b == "hostile":
			behavior = MobBehaviorType.hostile
		else:
			raise ValueError(f"Invalid behavior type {b!r}")
		death_drops = d.get("death_drops", {})
		return MobType(name, HP, behavior, death_drops)

mob_types = {}

for mob_dict in mobs_dict:
	mob_types[mob_dict["name"]] = MobType.from_dict(mob_dict)
	
class Mob:
	
	def __init__(self, name, HP, behavior: MobBehaviorType, death_drops):
		self.name = name
		self.HP = HP
		self.behavior = behavior
		self.death_drops = death_drops
		
	@staticmethod
	def new_mob(typ: str):
		typ = mob_types[typ]
		return Mob(typ.name, typ.hp, typ.behavior, typ.death_drops)
	
	def damage(self, amount, player):
		self.HP -= amount
		if self.HP <= 0:
			print(f"The {self.name.lower()} is dead!")
			self.on_death(player)
			
	def on_death(self, player):
		if self.death_drops:
			got = {}
			for drop in self.death_drops:
				r = self.death_drops[drop]
				if isinstance(r, list):
					assert len(r) == 2, "A range must have exactly one start and one end"
					start, end = tuple(r)
					amount = random.randint(start, end)
				elif isinstance(r, int):
					amount = r
				else:
					raise TypeError("Amount must be an int or a 2-item list")
				got[drop] = amount
			print("You got: ")
			for item in got:
				print(f"{got[item]}x {item}")
				player.add_item(item, got[item])
class Player:
	
	def __init__(self):
		self.HP = 20
		self.hunger = 20
		self.saturation = 5
		self.inventory = {}
		
	def damage(self, amount, death_reason=None):
		if amount <= 0:
			return
		print(f"You take {amount} damage!")
		self.HP -= amount
		if self.HP <= 0:
			print("You died!")
			if death_reason:
				print(death_reason)
			exit()
		print(f"HP: {self.HP}/20")
		
	def gain_health(self, amount):
		self.HP += amount
		
	def add_item(self, item, amount=1):
		if item in self.inventory:
			self.inventory[item] += amount
		else:
			self.inventory[item] = amount
		
print("MINCERAFT" if one_in(10000) else "MINECRAFT") #Extremely rare easter egg ;D
print()
choice = choice_input("Play", "Quit")
if choice == 2:
	exit()
	
player = Player()

passive_mob_types = list(filter(lambda typ: mob_types[typ].behavior == MobBehaviorType.passive, mob_types))
while True:
	choice = choice_input("Explore", "Inventory")
	if choice == 1:
		print("You explore for a while.")
		if one_in(3):
			mob = Mob.new_mob(random.choice(passive_mob_types))
			mob_name = mob.name.lower()
			print(f"You found a {mob_name} while exploring.")
			if mob.behavior == MobBehaviorType.hostile and one_in(2):
				print("The {mob_name} attacks you!")
				player.damage(2)
			choice = choice_input("Attack", "Flee" if mob.behavior == MobBehaviorType.hostile else "Ignore")
			if choice == 1:
				run = 0
				while True:
					if run > 0:
						run -= 1
					if (run > 0 and one_in(3)) or one_in(5):
						print(f"You miss the {mob_name}.")
					else:
						print(f"You attack the {mob_name}.")
						mob.damage(random.randint(1, 3), player) #TODO: Add different types of swords, each doing different amounts of damage
						if mob.HP <= 0:
							break
						if mob.behavior == MobBehaviorType.passive:
							if not one_in(3) and run == 0:
								print(f"The {mob_name} starts running away.")
								run += random.randint(3, 5)
						else:
							print("The {mob_name} attacks you!")
							player.damage(random.randint(1, 4)) #TODO: Unhardcode this value and make it depend on the type of mob
					choice = choice_input("Attack", "Ignore" if mob.behavior == MobBehaviorType.passive else "Flee")
					if choice == 2:
						break
	elif choice == 2:
		if len(player.inventory) == 0:
			print("There is nothing in your inventory")
		else:
			print("Your inventory:")
			for item in player.inventory:
				print(f"{player.inventory[item]}x {item}")
		