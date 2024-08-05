import asyncio
from .pcm import loadWAVtoPCM

experiment_busy = loadWAVtoPCM("assets/experiment_busy.wav")

def one_at_a_time(func):
	lock = asyncio.Lock()

	async def wrapped(call):
		if lock.locked():
			await call.playPCM(experiment_busy)
			return
		async with lock:
			return await func(call)

	return wrapped