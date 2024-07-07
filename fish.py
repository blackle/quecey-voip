#!/usr/bin/env python3
import asyncio
from voip import loadWAVtoPCM, runVoipClient, RecordController
from datetime import datetime

def trimPCM(pcm):
	try:
		start = next(i for i, x in enumerate(pcm) if abs(x) > .005)
		end = next(len(pcm)-i-1 for i, x in enumerate(pcm[::-1]) if abs(x) > .005)
		return pcm[start:end]
	except:
		return []


async def fishCallHandler(call):
	now = datetime.now()
	await asyncio.sleep(0.1)
	if now.strftime("%I:%M") != "11:05":
		await call.playTone(800,.5)
		controller = RecordController()
		record = call.recordPCM(controller=controller)
		try:
			dtmf = await asyncio.wait_for(call.getDTMF(), 15)
		except:
			pass
		await call.playTone(800,.5)
		controller.stop()
		pcm = trimPCM(await record)
		await call.playPCM(pcm)
	else:
		pcm = loadWAVtoPCM("fish_not_ready.wav")
		await call.playPCM(pcm)
	await asyncio.sleep(1)
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