#!/usr/bin/env python3
from voip import runVoipClient, loadWAVtoPCM
from typing import List
import tempfile
import subprocess
import io
import asyncio

wpm = 160

def load_word_list(filename: str) -> List[str]:
	with open(f"assets/hangman/{filename}.txt") as f:
		return [line.strip() for line in f]

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


words_large = load_word_list("en-large")
assert len(set(words_large)) == len(words_large)
pitch_adjust = 60
# requires espeak
def play_speech(call, speech: str, loop: bool = False):
	process = subprocess.run(['espeak', '-v', 'english-north', '-p', str(pitch_adjust),
		'-s', str(wpm), speech.strip(), '--stdout'], stdout=subprocess.PIPE)
	if process.returncode != 0:
		return None
	return call.playPCM(loadWAVtoPCM(io.BytesIO(process.stdout)), loop = loop)

def guess_valuation(guess: str, candidates: List[str]) -> int:
	patterns = {}
	for candidate in candidates:
		pattern = 0
		for letter in candidate:
			pattern <<= 1
			pattern |= int(letter == guess)
		patterns.setdefault(pattern, 0)
		patterns[pattern] += 1
	return -max(patterns.values())

def get_best_guess(candidates: List[str]) -> str:
	return max(alphabet, key = lambda letter: guess_valuation(letter, candidates))


async def play_index_set(call, indices):
	positions = sorted(index + 1 for index in indices)
	if len(positions) == 0:
		await call.playPCM(nowhere_pcm)
		return
	if len(positions) == 1:
		await call.playPCM(position_pcm)
		await asyncio.sleep(0.2)
		await call.playPCM(numbers_pcm[positions[0]])
		return
	await call.playPCM(positions_pcm)
	await asyncio.sleep(0.2)
	for position in positions[:-1]:
		await call.playPCM(numbers_pcm[position])
		await asyncio.sleep(0.2)
	await call.playPCM(and_pcm)
	await asyncio.sleep(0.2)
	await call.playPCM(numbers_pcm[positions[-1]])
	return
	
	
debug = False

async def handler(call):
	word_length = None
	prompt_promise = call.playPCM(intro_pcm, loop = True)
	word_length = int(await call.getDTMF(filter = '23456789'))
	prompt_promise.cancel()
	prompt_promise = None
	candidates = [word for word in words_large if len(word) == word_length]
	while len(candidates) > 1:
		guess = get_best_guess(candidates)
		if prompt_promise:
			prompt_promise.cancel()
			prompt_promise = None
		prompt_promise = call.playPCM(letters_pcm[guess], loop=True)
		indices = set()
		while True:
			position = int(await call.getDTMF(filter = '0123456789'))
			if position == 0: break
			index = position - 1
			if index in indices:
				indices.remove(index)
			else:
				indices.add(index)
			if prompt_promise:
				prompt_promise.cancel()
				prompt_promise = None
			prompt_promise = asyncio.ensure_future(play_index_set(call, indices))
		candidates = [candidate for candidate in candidates \
			if {i for i in range(len(candidate)) if candidate[i] == guess} == indices]
		assert len(candidates) == len(set(candidates))
		if debug:
			if len(candidates) > 5:
				await play_speech(call, f'There are {str(len(candidates))} candidates.')
			else:
				await play_speech(call, f'The candidates are ' + ', '.join(candidates) + '.')
	if prompt_promise:
		prompt_promise.cancel()
		prompt_promise = None
	if len(candidates) == 0:
		await call.playPCM(giveup_pcm)
	else:
		word = candidates[0]
		await call.playPCM(word_pre_pcm)
		await play_speech(call, word)
		await asyncio.sleep(0.2)
		await call.playPCM(word_post_pcm)

if __name__ == "__main__":
	runVoipClient(handler)
