#!/usr/bin/env python3

# save common sounds to wav files

import subprocess, os

wpm = 160
alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
nato = {
	'A': 'Alfa',
	'B': 'bravo',
	'C': 'Charlie',
	'D': 'delta',
	'E': 'echo',
	'F': 'foxtrot',
	'G': 'golf',
	'H': 'hotel',
	'I': 'India',
	'J': 'Juliett',
	'K': 'kilo',
	'L': 'Lima',
	'M': 'Mike',
	'N': 'November',
	'O': 'Oscar',
	'P': 'papa',
	'Q': 'Quebec',
	'R': 'Romeo',
	'S': 'Sierra',
	'T': 'tango',
	'U': 'uniform',
	'V': 'Victor',
	'W': 'whiskey',
	'X': 'X-ray',
	'Y': 'Yankee',
	'Z': 'Zulu',
}
numbers = {
	'1': 'one',
	'2': 'two',
	'3': 'three',
	'4': 'four',
	'5': 'five',
	'6': 'six',
	'7': 'seven',
	'8': 'eight',
	'9': 'nine',
}
speeches = {}

for letter in alphabet:
	speech = f"I'll guess {letter}, as in {nato[letter]}"
	speeches[letter] = speech

speeches['intro'] = """
Welcome to hang man. Think of a word up to 9 letters long. When you're ready,
dial the number of letters in your word.$
"""
speeches['giveup'] = "I give up! I don't know that word! Bye!"
speeches['prompt'] = """
Please enter all the letter positions where it appears in your word; then press zero.$
"""
speeches['wordpre'] = "I think your word is..."
speeches['wordpost'] = "Thanks for playing hangman!"
speeches['nowhere'] = 'nowhere'
speeches['position'] = 'position'
speeches['positions'] = 'positions'
speeches['and'] = 'and'
for number, word in numbers.items():
	speeches[number] = word

for filename in speeches:
	speech = speeches[filename].strip()
	speeches[filename] = (speech.strip('$'), '$' in speech)

for filename, (speech, silence) in speeches.items():
	print(f'Generating {filename}.wav...')
	subprocess.run(['espeak', '-s', str(wpm),  '-p', '60', '-v', 'english-north', speech.strip(), '-w', f'{filename}.wav'])
	if silence: 
		print(f'Adding silence to end of {filename}.wav...')
		subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f'{filename}.wav', '-af', 'apad=pad_dur=3', f'{filename}2.wav'])
		os.replace(f'{filename}2.wav', f'{filename}.wav')
