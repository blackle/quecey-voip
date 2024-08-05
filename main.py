#!/usr/bin/env python3
import asyncio
from voip import runVoipClient, loadWAVtoPCM
import phoneventure
import test
import echo
import dialasong
import hangman
import makeafish
EXPERIMENTS = {
	"1234": phoneventure.handler,
	"9999": echo.handler,
	"0000": test.handler,
	"6962": dialasong.handler,
	"4264": hangman.handler,
	"1111": makeafish.handler,
}

snd_enter_experiment = loadWAVtoPCM("assets/enter_experiment.wav")
snd_invalid_experiment = loadWAVtoPCM("assets/invalid_experiment.wav")
snd_teleport = loadWAVtoPCM("assets/teleport.wav")

async def handler(call):
	await call.playPCM(snd_enter_experiment)
	await call.playTone(1000, .25)
	try:
		code = await asyncio.wait_for(call.getDTMF(filter="0123456789", n=4), 60)
	except TimeoutError:
		code = ""
	if code in EXPERIMENTS:
		await call.playPCM(snd_teleport)
		await EXPERIMENTS[code](call)
	else:
		await call.playPCM(snd_invalid_experiment)

if __name__ == "__main__":
	runVoipClient(handler)
