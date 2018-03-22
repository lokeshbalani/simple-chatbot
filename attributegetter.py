from nltk.tag import StanfordNERTagger
from pycorenlp import StanfordCoreNLP
from nltk import sent_tokenize, word_tokenize
import marisa_trie
import re
import datetime
import os
nlp = StanfordCoreNLP('http://localhost:9000')


def loadCities(path):
	with open(path) as f:
		lines = f.readlines()
		cities = {}
		for i,line in enumerate(lines):
			lines[i] = line[:-1]
			code = line.split(':')[0].strip()
			synonyms = line.split(':')[1].strip().split(',')
			for i in range(len(synonyms)):
				synonyms[i] = synonyms[i].strip().lower()
			cities[code]=synonyms
		
		total = []
		for i in cities.keys():
			total += cities[i]
		total += cities.keys()
		for i in range(len(total)):
			total[i] = total[i].lower()
		trie = marisa_trie.Trie(total)
		return trie, cities
	
	return None, None

def markCities(text, trie, cities):

	text = text.lower().split()
	
	marks = []
	
	i=0
	while i<len(text):
		for j in range(len(text)-1,i-1, -1):
			#print ' '.join(text[i:j+1])
			if ' '.join(text[i:j+1]) in trie:
				marks += [(i,j)]
				i = j
				break
		i+=1
	
	startinds = []
	endinds = []
	ntext = []

	for i in marks:
		startinds += [i[0]]
		endinds += [i[1]]
	i=0
	while i < len(text):
		if i in startinds:
			ntext+=[ 'LOC_' + '_'.join(text[i : endinds[startinds.index(i)] +1 ])]
			i = endinds[startinds.index(i)]
		else:
			ntext += [text[i]]
		i+=1
	   
	
	ntext = ' '.join(ntext)

	return ntext

def writeFromTo(ntext, context):#(ntext, context, "key1","KeyMarker1", "key2", "keyMarker2")

	annsents = []
	tokens = word_tokenize(ntext)
	#print tokens

	for x, i in enumerate(tokens):
		if i.lower()=='from':
			for j in range(x+1, len(tokens)):
				if tokens[j].lower()=='to' or tokens[j].lower=='from':
					break
				if tokens[j].startswith('LOC_'):
					print("from location")
					tokens[j]='@From_' + tokens[j]
					break
		if i.lower()=='to':
			for j in range(x+1, len(tokens)):
				if tokens[j].lower()=='from' or tokens[j].lower()=='to':
					break
				if tokens[j].startswith('LOC_'):
					tokens[j] = '@To_' + tokens[j]
					break

	#######CHECK IF BOTH TO AND FROM FOUND. IF ONE OF THEM MISSING AND TO LOCATIONS FOUND THEN MARK THE OTHER ONE
	ct = 0
	_from = False
	_to = False

	for i in tokens:
		if i.startswith('@From'):
			_from = True
		elif i.startswith('@To'):
			_to = True
		if i.startswith('LOC_'):
			ct+=1
	
	if context.name.endswith('To'):
		if ct==1:
			for j, i in enumerate(tokens):
				if i.startswith('LOC_'):
					if _to==False:
						tokens[j] = '@To_' + tokens[j]
						_to = True
					elif _from==False:
						tokens[j] = '@From_' + tokens[j]
						_from = True

		elif ct==2:
			for j, i in enumerate(tokens):
				if i.startswith('LOC_'):
					if _from==False:
						tokens[j] = '@From_'  + tokens[j]
						_from = True
					elif _to==False:
						tokens[j] = '@To_' + tokens[j]
						_to = True
		
	else:
		if ct==1:
			for j, i in enumerate(tokens):
				if i.startswith('LOC_'):
					if _from==False:
						tokens[j] = '@From_' + tokens[j]
						_from = True
					elif _to==False:
						tokens[j] = '@To_' + tokens[j]
						_to = True

		elif ct==2:
			for j, i in enumerate(tokens):
				if i.startswith('LOC_'):
					if _from==False:
						tokens[j] = '@From_'  + tokens[j]
						_from = True
					elif _to==False:
						tokens[j] = '@To_' + tokens[j]
						_to = True
	
	return tokens


def getlocation(uinput, trie, cities, context,attributes,matches):

	text = ' '.join(word_tokenize(uinput))
	marked_input = markCities(text, trie, cities)
	# print marked_input
	marked_input = writeFromTo(marked_input, context)

	print(marked_input)

	
	for i in marked_input:
		if i.startswith('@'):
			for k,v in cities.iteritems():
				if str('_'.join(i.split('_')[2:])) in v:
					attributes[i.split('_')[0][1:]] = k
			matches['Location'].append('_'.join(i.split('_')[2:]))
	
	#print attributes
	return attributes,matches

	sents = sent_tokenize(uinput)
# print sents

def getdate(uinput,context,attributes,matches):

	uinput = uinput.lower()
	no_patterns = 0

	monthlist = ['jan','january','feb','feburary','mar','march','apr','april','may','may','jun','june','jul','july','aug','august','sep','september','oct','october','nov','november','dec','december']
	weekdaylist = ['monday','mon','tuesday','tue','wednesday','wed','thursday','thu','friday','fri','saturday','sat','sunday','sun']


	nexttodate_pattern = '((r)(d)|(t)(h)|(n)(d))?'
	of_pattern = '((\s+)(o)(f))?'

	date_pattern1 = '([0-9]+)'
	month_pattern1 = '((\s+)(?:january|jan|feburary|feb|march|mar|april|apr|may|may|june|jun|july|jul|august|aug|september|sep|october|oct|november|nov|december|dec))'
	pattern1 = re.compile(date_pattern1+nexttodate_pattern+of_pattern+month_pattern1)
	no_patterns = no_patterns + 1

	date_pattern2 = '(([0-9])+(/|-))'
	month_pattern2 = '(([0-9])+(/|-))'
	year_pattern2 = '([0-9]+)'
	pattern2 = re.compile(date_pattern2+month_pattern2+year_pattern2)
	no_patterns = no_patterns + 1

	date_pattern3 = '((\s+)[0-9]+)'    
	month_pattern3 = '(?:jan|january|feb|feburary|mar|march|apr|april|may|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)'
	pattern3 = re.compile(month_pattern3+ date_pattern3+nexttodate_pattern)
	no_patterns = no_patterns + 1

	pattern4 = re.compile('(?:day after tomorrow|tomorrow)')

	next_pattern = '(next)'
	next_week_month_pattern = '(?:week|month)'
	pattern5 = re.compile(next_pattern+'(\s+)'+next_week_month_pattern)


	date_pattern6 = '([0-9]+)'
	next_month_pattern = '((\s+)(next month))'
	pattern6 = re.compile(date_pattern6+nexttodate_pattern+of_pattern+next_month_pattern)


	pattern7 = re.compile('(today)')

	weekday_pattern = '(?:monday|mon|tuesday|tue|wednesday|wed|thursday|thu|friday|fri|saturday|sat|sunday|sun)'
	next_week_pattern = '((\s+)(next week))'
	pattern8 = re.compile(weekday_pattern+of_pattern+next_week_pattern)

	date = re.search(pattern8,uinput)
	if(date!=None):
		matches['Date'].append(date.group())
		weekday = re.search(weekday_pattern,date.group())
		weekday = weekdaylist.index(weekday.group())/2 + 1
		deltadays = 6 + (weekday-datetime.date.today().weekday())
		date = datetime.date.today() + datetime.timedelta(deltadays)
		attributes['Date'] = date
		return attributes,matches

	date = re.search(pattern7,uinput)
	if(date!=None):
		matches['Date'].append(date.group())
		date = datetime.date.today()
		attributes['Date'] = date
		return attributes,matches

	date = re.search(pattern6,uinput)
	if(date!=None):
		matches['Date'].append(date.group())
		day = re.search(date_pattern6,date.group()).group()
		date = datetime.date(year=datetime.date.today().year,day=int(day),month=datetime.date.today().month + 1)
		attributes['Date'] = date
		return attributes,matches

	date = re.search(pattern5,uinput)
	if(date!=None):
		matches['Date'].append(date.group())

		if(date.group()=="next week"):
			date = datetime.date.today()
			date = date + datetime.timedelta(7-date.weekday())

		else:
			date = datetime.date(year=datetime.date.today().year,day=1,month=datetime.date.today().month + 1)
		attributes['Date'] = date
		return attributes,matches

	date = re.search(pattern4,uinput)
	if(date!=None):
		matches['Date'].append(date.group())
		if(date.group()=="day after tomorrow"):
			date = datetime.date.today() + datetime.timedelta(days=2)
		else:
			date = datetime.date.today() + datetime.timedelta(days=1)
		attributes['Date'] = date
		return attributes,matches

	date = re.search(pattern2,uinput)
	if(date!=None):
		matches['Date'].append(date.group())
		date = date.group()
		year = date.split('/')[2]
		day = date.split('/')[0]
		month = date.split('/')[1]
		try:
			date = datetime.date(year=int(year),month=int(month),day=int(day))
			attributes['Date'] = date
			return attributes,matches
		except ValueError as e:
			print(e)
			return attributes,matches


	date = re.search(pattern1,uinput)
	if(date!=None):
		matches['Date'].append(date.group())

		date = date.group()
		day = re.search(date_pattern1,date)
		month = re.search(month_pattern1,date)
		year = datetime.date.today().year
		month = monthlist.index(month.group().strip())/2+ 1
		try:
			date = datetime.date(year=year,month=month,day=int(day.group()))
			attributes['Date'] = date
			return attributes,matches
		except ValueError as e:
			print(e)
			return attributes,matches

	date = re.search(pattern3,uinput)
	if(date!=None):
		matches['Date'].append(date.group())

		date = date.group()
		day = re.search(date_pattern3,date)
		month = re.search(month_pattern3,date)
		year = datetime.date.today().year

		month = monthlist.index(month.group().strip())/2+ 1
		try:
			date = datetime.date(year=year,month=month,day=int(day.group()))
			attributes['Date'] = date
			return attributes,matches
		except ValueError as e:
			print(e)
			return attributes,matches

	return attributes,matches

def getNames(uinput, context,matches):
	st = StanfordNERTagger('english.all.3class.distsim.crf.ser.gz')
	NERTags = st.tag(word_tokenize(uinput))
	names = []
	i=0
	flag = 0
	#print NERTags
	while i<len(NERTags):
		#print i
		if NERTags[i][1]=='PERSON':
			names += [NERTags[i][0]]
			for j in range(i+1, len(NERTags)):
				if NERTags[j][1]=='PERSON':
					names[-1]+= ' '+NERTags[j][0]
					if j==len(NERTags)-1:
						flag = 1
				else:
					i=j
					break
		if flag==1:
			break
		i = i+1
	for name in names:
		matches['Name'].append(name)
	return names,matches

def getattributes(uinput,context,attributes):
	
	if context.name.startswith('IntentComplete'):
		return attributes, uinput
	else:

		files = os.listdir('./entities/')
		entities = {}
		for fil in files:
			lines = open('./entities/'+fil).readlines()
			for i, line in enumerate(lines):
				lines[i] = line[:-1]
			entities[fil[:-4]] = lines

		matches = {}

		for entity in entities:
			entities[entity]
			for entity in entities:
				print(entities)
			uinput = re.sub(matches,r'$person',uinput,flags=re.IGNORECASE)

		#continue

		uinput_tokenized = word_tokenize(uinput)
		if context.name=='FirstGreeting':
			names,matches = getNames(uinput,context,matches)
			# uinput_tokenized = replaceNames(uinput_tokenized, context)   
			if names!=[]:
				attributes['PassengerName'] = names[0]

			# print matches,"after checking names"
			cities_trie, cities_dict = loadCities('./data/cities.dat')
			attributes,matches = getlocation(uinput,cities_trie,cities_dict,context,attributes,matches)
			# uinput_tokenized = replacelocation(uinput.split(),cities_trie, cities_dict, context)
			# print matches,"after checking location"
			attributes,matches = getdate(uinput,context,attributes,matches)
			# uinput_tokenized = getdate(uinput.split(),context,attributes,True)
			# print matches,"after replacing date"

			# print uinput



			for match in matches['Name']:
				uinput = re.sub(match,r'$person',uinput,flags=re.IGNORECASE)

			for match in matches['Date']:
				uinput = re.sub(match,r'$date',uinput,flags=re.IGNORECASE)

			for match in matches['Location']:
				uinput = re.sub(match,r'$location',uinput,flags=re.IGNORECASE)
			
			return attributes,uinput
			# cleaned_input = replaceplaceholders(uinput)

		if '_'.join(context.name.split('_')[2:])=='From':
			cities_trie, cities_dict = loadCities('./data/cities.dat')
			attributes,matches = getlocation(uinput,cities_trie, cities_dict, context,attributes,matches)

		if '_'.join(context.name.split('_')[2:])=='To':
			cities_trie, cities_dict = loadCities('./data/cities.dat')
			attributes,matches = getlocation(uinput,cities_trie, cities_dict, context,attributes,matches)

		if '_'.join(context.name.split('_')[2:])=='Date':
			attributes,matches = getdate(uinput,context,attributes,matches)

		if '_'.join(context.name.split('_')[2:])=='PassengerName':
			names,matches = getNames(uinput, context,matches)   
			if names!=[]:
				attributes['PassengerName'] = names[0]
				

		return attributes, uinput
