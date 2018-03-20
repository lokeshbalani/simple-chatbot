#from textblob import TextBlob
#from attributegetter import *
from generatengrams import ngrammatch
from Contexts import *
import json
from Intents import *
import random
import os
import re

def check_actions(current_intent, attributes, context):
    '''This function performs the action for the intent
    as mentioned in the intent config file'''
    '''Performs actions pertaining to current intent
    for action in current_intent.actions:
        if action.contexts_satisfied(active_contexts):
            return perform_action()
    '''

    context = IntentComplete()
    return 'action: ' + current_intent.action, context

def check_required_params(current_intent, attributes, context):
    '''Collects attributes pertaining to the current intent'''
    
    for para in current_intent.params:
        if para.required:
            if para.name not in attributes:
                if para.name=='RegNo':
                    context = GetRegNo()
                return random.choice(para.prompts), context

    return None, context


def input_processor(user_input, context, attributes, intent):
    '''Spellcheck and entity extraction functions go here'''
    
    uinput = TextBlob(user_input).correct().string
    
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
    scores = sorted_by_second = sorted(scores, key=lambda tup: tup[1])
    # print clean_input
    #print 'scores', scores
    

    if(current_intent==None):
        if(clean_input=="search"):
            return loadIntent('params/newparams.cfg', 'SearchStore')
        if(clean_input=='book'):
            return loadIntent('params/newparams.cfg','OrderBook')
        else:
            return loadIntent('params/newparams.cfg',scores[-1][0])
    else:
        #print 'same intent'
        return current_intent

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

        if context.name=='GetRegNo'  and context.active:
            match = re.search('[0-9]+', uinput)
            if match:
                uinput = re.sub('[0-9]+', '$regno', uinput)
                attributes['RegNo'] = match.group()
                context.active = False

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

session = Session()

print 'BOT: Hi! How may I assist you?'

while True:
    
    inp = raw_input('User: ')
    print 'BOT:', session.reply(inp)

