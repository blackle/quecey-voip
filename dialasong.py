#!/usr/bin/env python3
from voip import *
import asyncio
from dataclasses import dataclass
from voip.pcm import packedToFloat
import wave
import io
import os
import sys
import subprocess
import shutil
import struct
import random

@dataclass
class Song:
	title: str
	artist: str
	url: str

songs = [
	Song('Never Gonna Give You Up', 'Rick Astley', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'),
	Song('Istanbul (Not Constantinople)', 'They Might Be Giants', 'https://www.youtube.com/watch?v=p6NzVd3pGdE'),
	Song('Don\'t Forget', 'Laura Shigihara', 'https://www.youtube.com/watch?v=PEPbUhHhECU'),
	Song('All Star', 'Smash Mouth', 'https://www.youtube.com/watch?v=-_RBJvfoszk')
]

random.seed()

async def handler(call):
	idx = random.randrange(len(songs))
	song = songs[idx]

	await call.playPCM(TTStoPCM(f'Now playing: {song.title} by {song.artist}'))

	ytdlp = subprocess.Popen(
		[
			shutil.which("yt-dlp"),
			"-o-",
			song.url,
		],
		stdout=subprocess.PIPE,
		stderr=subprocess.DEVNULL,
	)
	ffmpeg = subprocess.Popen(
		[
			shutil.which('ffmpeg'),
			'-i', '-',
			'-acodec', 'pcm_s16le',
			'-ar', '8000',
			'-f', 's16le',
			'-'
		],
		stdin=ytdlp.stdout,
		stdout=subprocess.PIPE,
		stderr=subprocess.DEVNULL,
	)

	def songPlayer(t, delta):
		try:
			data = ffmpeg.stdout.read(4)
			if len(data) < 4:
				raise EOFError
			(l, r) = struct.unpack('<hh', data)
			return (l + r) / 65536
		except EOFError:
			return None
		
	await call.playCustom(songPlayer)
	await call.playPCM(TTStoPCM('Thank you for listening. Goodbye!'))


if __name__ == '__main__':
	runVoipClient(handler)