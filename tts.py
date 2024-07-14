#!/usr/bin/env python3
import asyncio
import queue
import subprocess
import io
from voip import runVoipClient, loadWAVtoPCM

def TTStoPCM(text, opts=[]):
	process = subprocess.run(["espeak", "--stdout", *opts, text], stdout=subprocess.PIPE, timeout=1)
	data = process.stdout
	return loadWAVtoPCM(io.BytesIO(data))

async def handler(call):
	await call.playPCM(TTStoPCM("this is a test of speech to text", opts=['-v', 'Storm']))

if __name__ == "__main__":
	runVoipClient(handler)