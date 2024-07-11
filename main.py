#!/usr/bin/env python3
import asyncio
from voip import runVoipClient, loadWAVtoPCM
import phoneventure
import fish
import test
import echo

EXPERIMENTS = {
	"1234": phoneventure.handler,
	"1111": fish.handler,
	"9999": echo.handler,
	"0000": test.handler,
}

async def handler(call):
	try:
		code = await asyncio.wait_for(call.getDTMF(filter="0123456789", n=4), 60)
	except TimeoutError:
		code = ""
	if code in EXPERIMENTS:
		await call.playPCM(loadWAVtoPCM("assets/teleport.wav"))
		await EXPERIMENTS[code]
	else:
		await call.playPCM(loadWAVtoPCM("assets/invalid_experiment.wav"))

if __name__ == "__main__":
	runVoipClient(handler)