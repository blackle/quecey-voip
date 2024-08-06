#!/usr/bin/env python3
from voip import runVoipClient, loadWAVtoPCM, TTStoPCM
from typing import List, Set
import tempfile
import subprocess
import io
import asyncio

# voice words per minute
wpm = 160
# voice pitch adjust (0-100)
pitch_adjust = 60
debug = False


# Load a bunch of sounds into memory
intro_pcm = loadWAVtoPCM("assets/hangman/intro.wav")
nowhere_pcm = loadWAVtoPCM("assets/hangman/intro.wav")
prompt_pcm = loadWAVtoPCM("assets/hangman/prompt.wav")
giveup_pcm = loadWAVtoPCM("assets/hangman/giveup.wav")
word_pre_pcm = loadWAVtoPCM("assets/hangman/wordpre.wav")
word_post_pcm = loadWAVtoPCM("assets/hangman/wordpost.wav")
letters_pcm = {}
alphabet = 'abcdefghijklmnopqrstuvwxyz'
for letter in alphabet:
	letters_pcm[letter] = loadWAVtoPCM(f"assets/hangman/{letter.upper()}.wav") + prompt_pcm
numbers_pcm = {}
for number in '123456789':
	numbers_pcm[int(number)] = loadWAVtoPCM(f"assets/hangman/{number}.wav")
nowhere_pcm = loadWAVtoPCM("assets/hangman/nowhere.wav")
positions_pcm = loadWAVtoPCM("assets/hangman/positions.wav")
position_pcm = loadWAVtoPCM("assets/hangman/position.wav")
and_pcm = loadWAVtoPCM("assets/hangman/and.wav")

# load the word list
def load_word_list(filename: str) -> List[str]:
	with open(f"assets/hangman/{filename}.txt") as f:
		return [line.strip() for line in f]

words_large = load_word_list("en-large")
if debug:
	assert len(set(words_large)) == len(words_large)

# requires espeak
def play_speech(call, speech: str, loop: bool = False):
	''' Play text speech over the call. '''
	pcm = TTStoPCM(speech.strip(), engine = 'rhvoice', opts = ['-p', 'slt'])
	return call.playPCM(pcm, loop = loop)

def guess_valuation(guess: str, candidates: List[str]) -> int:
	''' Returns how good we think this guess is, given the list of candidate words. '''
	# `patterns` maps a bit mask like (1 << 2 | 1 << 3) to the number of words which have
	# `guess` at the 2nd and 3rd index.
	patterns = {}
	for candidate in candidates:
		# pattern = bit mask of where `guess` appears in `candidate`
		pattern = 0
		for letter in candidate:
			pattern <<= 1
			pattern |= int(letter == guess)
		patterns.setdefault(pattern, 0)
		patterns[pattern] += 1
	# we want to minimize the maximum possible number of candidates following
	# our guess. so the rarer the most common pattern is, the better.
	return -max(patterns.values())

def get_best_guess(candidates: List[str]) -> str:
	''' Pick the best(/ a very good) letter to guess next, given the candidate words. '''
	return max(alphabet, key = lambda letter: guess_valuation(letter, candidates))


async def play_index_set(call, indices: Set[int]):
	''' Play some speech like "Positions 1, 3, and 4" for the index set [0, 2, 3]. '''
	positions = sorted(index + 1 for index in indices)
	if len(positions) == 0:
		# "Nowhere"
		await call.playPCM(nowhere_pcm)
		return
	if len(positions) == 1:
		# "Position X"
		await call.playPCM(position_pcm)
		await asyncio.sleep(0.2)
		await call.playPCM(numbers_pcm[positions[0]])
		return
	# "Positions..."
	await call.playPCM(positions_pcm)
	for position in positions[:-1]:
		await asyncio.sleep(0.2)
		await call.playPCM(numbers_pcm[position])
	# ", and"
	await asyncio.sleep(0.1)
	await call.playPCM(and_pcm)
	await asyncio.sleep(0.1)
	# Last position
	await call.playPCM(numbers_pcm[positions[-1]])
	return
	
	
async def handler(call):
	# Play intro message
	prompt_future = call.playPCM(intro_pcm, loop = True)
	# Get word length
	word_length = int(await call.getDTMF(filter = '23456789'))
	prompt_future.cancel()
	prompt_future = None
	# Get list of candidate words (number of words matching the given length)
	candidates = [word for word in words_large if len(word) == word_length]
	while len(candidates) > 1:
		if prompt_future:
			prompt_future.cancel()
			prompt_future = None
		# Make a guess
		guess = get_best_guess(candidates)
		prompt_future = call.playPCM(letters_pcm[guess], loop=True)
		# Wait for callee to enter all the positions
		indices = set()
		while True:
			position = int(await call.getDTMF(filter = '0123456789'))
			if position == 0: break
			index = position - 1
			if index in indices:
				indices.remove(index)
			else:
				indices.add(index)
			if prompt_future:
				prompt_future.cancel()
				prompt_future = None
			prompt_future = asyncio.ensure_future(play_index_set(call, indices))
		# Update list of candidates
		candidates = [candidate for candidate in candidates \
			if {i for i in range(len(candidate)) if candidate[i] == guess} == indices]
		if debug:
			assert len(candidates) == len(set(candidates))
			if len(candidates) > 5:
				await play_speech(call, f'There are {str(len(candidates))} candidates.')
			else:
				await play_speech(call, f'The candidates are ' + ', '.join(candidates) + '.')
	if prompt_future:
		prompt_future.cancel()
		prompt_future = None
	if len(candidates) == 0:
		# no such words (or callee cheated) :C
		await call.playPCM(giveup_pcm)
	else:
		# We got the word! (probably)
		word = candidates[0]
		await call.playPCM(word_pre_pcm)
		await play_speech(call, word)
		await asyncio.sleep(0.2)
		await call.playPCM(word_post_pcm)

if __name__ == "__main__":
	runVoipClient(handler)
