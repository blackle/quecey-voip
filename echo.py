#!/usr/bin/env python3
import asyncio
import pickle
import queue
from voip import runVoipClient

async def handler(call):
	sampleQueue = queue.Queue(maxsize=16000*2)
	stop = False
	def sampleInput(sample):
		if stop:
			return False
		if not sampleQueue.full():
			sampleQueue.put(sample)
		return True
	def sampleOutput(t, delta):
		if stop:
			return None
		if sampleQueue.qsize() < 160:
			return 0
		return sampleQueue.get()
	call.recordCustom(sampleInput)
	call.playCustom(sampleOutput)
	await call.getDTMF()


if __name__ == "__main__":
	runVoipClient(handler)