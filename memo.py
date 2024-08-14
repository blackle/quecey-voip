#!/usr/bin/env python3
import asyncio
import os
from voip import loadWAVtoPCM, savePCMtoWAV, runVoipClient, RecordController, normalizePCM

memo_intro = loadWAVtoPCM("assets/memo_intro.wav")
memo_record = loadWAVtoPCM("assets/memo_record.wav")

async def handler(call):
	code = ""
	playback = call.playPCM(memo_intro)
	while True:
		key = await call.getDTMF(filter="0123456789#")
		print(f"got key {key}")
		playback.cancel()
		if key == '#':
			break
		code += key
	if len(code) == 0:
		return
	memo_path = f"./memos/{code}.wav"
	if os.path.exists(memo_path):
		await call.playPCM(loadWAVtoPCM(memo_path))
	else:
		playback = call.playPCM(memo_record)
		key = await call.getDTMF(filter="#")
		playback.cancel()
		await call.playTone(1000,.25)
		controller = RecordController()
		await asyncio.sleep(0.1)
		record = call.recordPCM(controller=controller)
		try:
			dtmf = await asyncio.wait_for(call.getDTMF(), 120)
		except TimeoutError:
			await call.playTone(900,.1)
			await asyncio.sleep(0.1)
			await call.playTone(900,.1)
			await asyncio.sleep(0.1)
			await call.playTone(900,.1)
			await asyncio.sleep(0.5)
			controller.stop()
			return
		controller.stop()
		pcm = normalizePCM(await record)
		savePCMtoWAV(pcm, memo_path)

if __name__ == "__main__":
	runVoipClient(handler)
