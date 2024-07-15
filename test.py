#!/usr/bin/env python3
import asyncio
from voip import runVoipClient, loadWAVtoPCM

async def handler(call):
	await call.playTone(420, .5)
	await asyncio.sleep(.5)
	await call.playTone(560, .5)
	await asyncio.sleep(.5)
	await call.playTone(650, .5)
	await asyncio.sleep(.5)
	try:
		code = await asyncio.wait_for(call.getDTMF(n = 4), 60)
	except TimeoutError:
		code = ""
	if code == "1234":
		await call.playPCM(loadWAVtoPCM("assets/password_correct.wav"))
	else:
		await call.playPCM(loadWAVtoPCM("assets/password_incorrect.wav"))

if __name__ == "__main__":
	runVoipClient(handler)
