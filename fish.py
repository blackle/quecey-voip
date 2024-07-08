#!/usr/bin/env python3
import asyncio
from voip import loadWAVtoPCM, runVoipClient, RecordController
from datetime import datetime

def normalizePCM(pcm):
	try:
		start = next(i for i, x in enumerate(pcm) if abs(x) > .005)
		end = next(len(pcm)-i-1 for i, x in enumerate(pcm[::-1]) if abs(x) > .005)
		m = max(abs(x) for x in pcm)
		return [x / m for x in pcm[start:end]]
	except:
		return []

phone_tree = {
	"s": loadWAVtoPCM("phone_tree_trailhead.wav")
}

answer_missing = loadWAVtoPCM("phone_tree_answer_missing.wav")
author_instructions = loadWAVtoPCM("phone_tree_author_instructions.wav")
author_finalize = loadWAVtoPCM("phone_tree_author_finalize.wav")

async def fishCallHandler(call):
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
					record = call.recordPCM(controller=controller)
					try:
						dtmf = await asyncio.wait_for(call.getDTMF(), 60)
					except:
						dtmf = '#'
					controller.stop()
					pcm = normalizePCM(await record)
					await call.playTone(1333,.25)
					await call.playPCM(pcm)
					playback = call.playPCM(author_finalize)
					dtmf = await call.getDTMF()
					if dtmf == '1':
						phone_tree[tree_pos] = pcm





	# now = datetime.now()
	# await asyncio.sleep(0.1)
	# if now.strftime("%I:%M") != "11:05":
	# 	await call.playTone(800,.5)
	# 	controller = RecordController()
	# 	record = call.recordPCM(controller=controller)
	# 	try:
	# 		dtmf = await asyncio.wait_for(call.getDTMF(), 15)
	# 	except:
	# 		pass
	# 	controller.stop()
	# 	pcm = normalizePCM(await record)
	# 	await call.playTone(800,.5)
	# 	await call.playPCM(pcm)
	# else:
	# 	pcm = loadWAVtoPCM("fish_not_ready.wav")
	# 	await call.playPCM(pcm)
	# await asyncio.sleep(1)
	# try:
	# 	dtmf = await asyncio.wait_for(call.getDTMF(n=4), 15)
	# 	message.cancel()
	# 	if dtmf == "1312":
	# 		await call.playTone(1900,.4)
	# 		await asyncio.sleep(1)
	# except TimeoutError:
	# 	print("timeout")

if __name__ == "__main__":
	runVoipClient(fishCallHandler)