from generatengrams import ngrammatch
from Contexts import *
import json
from Intents import *
import random
import os
import re
import pandas as pd

HOTEL_REGEX = "(stay)|(hotel)|(room)|(motel)|(inn)"
RESTAURANT_REGEX = "(eat)|(party)|(table)|(food)|(veg)|(restaurant)|(hungry)|(starving)|(organic)|(cuisine)|(buffet)|(serve)"

def check_actions(current_intent, attributes, context):
	'''This function performs the action for the intent
	as mentioned in the intent config file'''
	'''Performs actions pertaining to current intent'''

	context = IntentComplete()
	
	if current_intent.action == 'BookRestaurant':
		#print(current_intent.action)
		return BookRestaurant(attributes), context
	if current_intent.action == 'BookHotel':
		return BookHotel(attributes), context

	return 'action: ' + current_intent.action, context

def check_required_params(current_intent, attributes, context):
	'''Collects attributes pertaining to the current intent'''
	
	for para in current_intent.params:
		if para.required:
			if para.name not in attributes:
				if para.name=='Tariff':
					context = GetTariff()
				return random.choice(para.prompts), context

	return None, context

def input_processor(user_input, context, attributes, intent):
	'''Spellcheck and entity extraction functions go here'''
	
	#uinput = TextBlob(user_input).correct().string
	
	#update the attributes, abstract over the entities in user input
	attributes, cleaned_input = getattributes(user_input, context, attributes)
	
	return attributes, cleaned_input

def loadIntent(path, intent):
	with open(path) as fil:
		dat = json.load(fil)
		intent = dat[intent]
		return Intent(intent['intentname'],intent['Parameters'], intent['actions'])

def intentIdentifier(clean_input, context,current_intent):
	clean_input = clean_input.lower()
	scores = ngrammatch(clean_input)
	scores  = sorted(scores, key=lambda tup: tup[1])
	# print clean_input
	#print 'scores', scores
	

	if(current_intent==None):
		if(re.search(RESTAURANT_REGEX, clean_input)):
			return loadIntent('params/newparams.cfg', 'RestaurantBooking')
		if(re.search(HOTEL_REGEX, clean_input)):
			return loadIntent('params/newparams.cfg','HotelBooking')
		else:
			return loadIntent('params/newparams.cfg',scores[-1][0])
	else:
		#print 'same intent'
		return current_intent

def process_tariff(uinput):
	regex_gt = r"(greater\s*than|gt|above|>|>\s*=)\s*([0-9]+)" 
	regex_lt = r"(less\s*than|below|lt|<|<\s*=)\s*([0-9]+)"
	regex_bt = r"(greater\s*than|less\s*than|below|gt|above|below|lt|around|between|range|<|>|<\s*=|>\s*=)?\s*([0-9]+)\s*(-|&|and|,|\s)?\s*([0-9]*)"
	regex_num = r"([0-9]+)"

	x = ""
	COMMA = ","

	match_gt = re.findall(regex_gt,uinput)
	match_lt = re.findall(regex_lt,uinput)
	match_bt = re.findall(regex_bt,uinput)
	match = re.findall(regex_num,uinput)

	if len(match_gt) and len(match_lt):
		for m in match_gt:
			m = list(m)
			m[0] = ">"
			for item in m:
				x += item
			x += COMMA

		for m in match_lt:
			m = list(m)
			m[0] = "<"
			for item in m:
				x += item
			x += COMMA
	elif len(match_gt):
		for m in match_gt:
			m = list(m)
			m[0] = ">"
			for item in m:
				x += item
			x += COMMA
	elif len(match_lt):
		for m in match_lt:
			m = list(m)
			m[0] = "<"
			for item in m:
				x += item
			x += COMMA
	elif len(match_bt):
		for m in match_bt:
			m = list(m)
			m[0]=">"
			m[2]="<"
			for i,item in enumerate(m):
				if (i + 1)%2 == 0:
					x += item + COMMA
				else:
					x += item
	else:
		for m in match:
			m = list(m)
			for item in m:
				x += item
			x += COMMA

	#print(x[:-1])
	return x[:-1]

def getattributes(uinput,context,attributes):
	'''This function marks the entities in user input, and updates
	the attributes dictionary'''
	#Can use context to to context specific attribute fetching
	if context.name.startswith('IntentComplete'):
		return attributes, uinput
	else:

		files = os.listdir('./entities/')
		entities = {}
		for fil in files:
			lines = open('./entities/'+fil).readlines()
			for i, line in enumerate(lines):
				lines[i] = line[:-1]
			entities[fil[:-4]] = '|'.join(lines)

		for entity in entities:
			for i in entities[entity].split('|'):
				if i.lower() in uinput.lower():
					attributes[entity] = i
		for entity in entities:
				uinput = re.sub(entities[entity],r'$'+entity,uinput,flags=re.IGNORECASE)

		if context.name=='GetTariff'  and context.active:
			#print('Tariff')
			match = process_tariff(uinput)
			uinput = re.sub(r'[<|>|<=|>=]?\s*[0-9]+\s*[-]?\s*[0-9]+', '$tariff', uinput)
			attributes['Tariff'] = match
			context.active = False
		
		#print(attributes)
		return attributes, uinput


class Session:
	def __init__(self, attributes=None, active_contexts=[FirstGreeting(), IntentComplete() ]):
		
		'''Initialise a default session'''
		
		#Contexts are flags which control dialogue flow, see Contexts.py
		self.active_contexts = active_contexts
		self.context = FirstGreeting()
		
		#Intent tracks the current state of dialogue
		#self.current_intent = First_Greeting()
		self.current_intent = None
		
		#attributes hold the information collected over the conversation
		self.attributes = {}
		
	def update_contexts(self):
		'''Not used yet, but is intended to maintain active contexts'''
		for context in self.active_contexts:
			if context.active:
				context.decrease_lifespan()

	def reply(self, user_input):
		'''Generate response to user input'''
		
		self.attributes, clean_input = input_processor(user_input, self.context, self.attributes, self.current_intent)
		
		self.current_intent = intentIdentifier(clean_input, self.context, self.current_intent)
		
		prompt, self.context = check_required_params(self.current_intent, self.attributes, self.context)

		#prompt being None means all parameters satisfied, perform the intent action
		if prompt is None:
			if self.context.name!='IntentComplete':
				prompt, self.context = check_actions(self.current_intent, self.attributes, self.context)
		
		#Resets the state after the Intent is complete
		if self.context.name=='IntentComplete':
			self.attributes = {}
			self.context = FirstGreeting()
			self.current_intent = None
		
		return prompt


# In[ ]:


def BookHotel(attributes):
	#constants
	HOTEL_DB_COL_MAP = {
		"hloc": "LOCATION",
		"starrating": "STAR RATING",
		"Tariff": "TARIFF"
	}
	
	db = pd.read_csv("./db/db_hotel.csv")
	
	for attr, val in attributes.items():
		col_name = HOTEL_DB_COL_MAP[attr]
		#print(val)
		if col_name == "TARIFF":
			val = val.split(",");
			
			for v in val:
				if ">" in v:
					v = v.replace(">", "").strip()
					db = db[db[col_name] > int(v)]
				if "<" in v:
					v = v.replace("<", "").strip()
					db = db[db[col_name] < int(v)]
				if "<=" in v:
					v = v.replace("<=", "").strip()
					db = db[db[col_name] <= int(v)]
				if ">=" in v:
					v = v.replace(">=", "").strip()
					db = db[db[col_name] >= int(v)]
				if "-" in v:
					v = v.split("-")
					db = db[db[col_name] < int(v[1].strip())]
					db = db[db[col_name] > int(v[0].strip())]
		else:       
			db = db[db[col_name] == val]

	hotel_names = db["HOTEL NAME"]
	output = ["List of Hotels matching your criterio\n"]
	
	if len(hotel_names):
		for i, hotel in enumerate(hotel_names):
			output.append("{}. {}".format(i + 1, hotel))
		
		return output
	else:
		return "No Hotels found for the provided parameters"
		
def BookRestaurant(attributes):
	#constants
	RESTAURANT_DB_COL_MAP = {
		"rloc": "LOCATION",
		"cuisine": "CUISINE",
		"cost": "COST"
	}
	
	db = pd.read_csv("./db/db_restaurant.csv")
	
	for attr, val in attributes.items():
		col_name = RESTAURANT_DB_COL_MAP[attr]
		db = db[db[col_name] == val]
	
	restaurant_names = db["RESTAURANT NAME"]
	output = ["List of Restaurants matching your criterion:\n"]
	
	if len(restaurant_names):
		for i, restaurant in enumerate(restaurant_names):
			output.append("{}. {}\n".format(i + 1, restaurant))
		
		return output
	else:
		return "No Restaurant found for the provided parameters"
	

session = Session()

print("RESTAURANT/HOTEL BOOKING PORTAL")
print("Welcome to the Hotel/Restaurant Booking Portal. What do you want to do?")
print("1. Book a Hotel")
print("2. Book a Restaurant\n\n")

print ('[Team 53 BOT]: Hi! How may I assist you?')

while True:
	
	inp = input('[User]: ')
	print ('[Team 53 BOT]:', session.reply(inp))

