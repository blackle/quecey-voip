#!/usr/bin/env python3
import asyncio
import pickle
from voip import loadWAVtoPCM, runVoipClient, RecordController, normalizePCM
from datetime import datetime

try:
	with open("phone_tree.pkl", 'rb') as file:
		phone_tree = pickle.load(file)
except (FileNotFoundError, pickle.UnpicklingError) as e:
	print("couldn't load saved tree:", e)
	phone_tree = {"s": loadWAVtoPCM("assets/phone_tree_trailhead.wav")}

def save_phone_tree(phone_tree):
	with open("phone_tree.pkl", 'wb') as file:
		pickle.dump(phone_tree, file)

answer_missing = loadWAVtoPCM("assets/phone_tree_answer_missing.wav")
author_instructions = loadWAVtoPCM("assets/phone_tree_author_instructions.wav")
author_finalize = loadWAVtoPCM("assets/phone_tree_author_finalize.wav")

async def handler(call):
	global phone_tree
	tree_pos = "s"
	playback = None
	while True:
		if playback is not None:
			playback.cancel()
		if tree_pos in phone_tree:
			pcm = phone_tree[tree_pos]
			playback = call.playPCM(pcm)
			await asyncio.sleep(0.25) #little bit of sleep for debounce
			dtmf = await call.getDTMF()
			if dtmf == '*':
				tree_pos = tree_pos[:-1]
				if tree_pos == "":
					break
			elif dtmf.isdigit():
				tree_pos += dtmf
		else:
			playback = call.playPCM(answer_missing)
			await asyncio.sleep(0.25) #little bit of sleep for debounce
			dtmf = await call.getDTMF()
			if dtmf == '*':
				tree_pos = tree_pos[:-1]
			elif dtmf == '#':
				playback.cancel()
				playback = call.playPCM(author_instructions)
				await asyncio.sleep(0.25) #little bit of sleep for debounce
				dtmf = await call.getDTMF()
				if dtmf == '*':
					tree_pos = tree_pos[:-1]
					continue
				while dtmf == '#':
					playback.cancel()
					await call.playTone(1000,.25)
					controller = RecordController()
					await asyncio.sleep(0.25)
					record = call.recordPCM(controller=controller)
					try:
						dtmf = await asyncio.wait_for(call.getDTMF(), 60)
					except:
						dtmf = '#'
					await asyncio.sleep(0.25)
					controller.stop()
					pcm = normalizePCM(await record)
					await call.playTone(1333,.25)
					await call.playPCM(pcm)
					playback = call.playPCM(author_finalize)
					dtmf = await call.getDTMF()
					if dtmf == '1':
						phone_tree[tree_pos] = pcm
						save_phone_tree(phone_tree)

if __name__ == "__main__":
	runVoipClient(handler)
