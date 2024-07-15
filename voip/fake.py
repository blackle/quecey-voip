import pyaudio
import asyncio
import time
from .pcm import floatToPacked, packedToFloat
from .engine import AudioEngine
from .dtmf import DTMF
from .iface import CallInterface
import curses

class FakeCall:
	def __init__(self):
		clockRate = 8000
		self.engine = AudioEngine(clockRate)
		self.dtmf = DTMF()
		self.remoteUri = "\"5556667777\" <sip:5556667777@localhost>"

		def input_callback(in_data, frame_count, time_info, status):
			samples = []
			for i in range(len(in_data)):
				if i % 2 == 1:
					x = packedToFloat(in_data[i], in_data[i-1])
					samples.append(x)

			self.engine.onFrameReceived(samples)
			return (None, pyaudio.paContinue)

		self.firstRun = False
		def output_callback(in_data, frame_count, time_info, status):
			samples = self.engine.onFrameRequested(frame_count) if not self.firstRun else None
			self.firstRun = False
			if samples is None:
				return (chr(0)*frame_count*2, pyaudio.paContinue)
			data = []
			for x in samples:
				low, hi = floatToPacked(x)
				data.append(low)
				data.append(hi)
			return (bytes(data), pyaudio.paContinue)

		self.p = pyaudio.PyAudio()

		self.input = self.p.open(input=True, format=pyaudio.paInt16, channels=1, rate=clockRate, stream_callback=input_callback)
		self.output = self.p.open(output=True, format=pyaudio.paInt16, channels=1, rate=clockRate, stream_callback=output_callback)

	def hangup(self):
		self.input.close()
		self.output.close()
		self.p.terminate()

class RateLimiter():
	def __init__(self, ns):
		self.ns = ns
		self.then = time.time_ns()

	def check(self):
		now = time.time_ns()
		if (now - self.then) > self.ns:
			self.then = now
			return True
		return False

def runVoipClientReal(screen, taskFunction):
	screen.nodelay(True)
	loop = asyncio.get_event_loop()

	call = FakeCall()

	async def call_func(call):
		iface = CallInterface(call, call.dtmf, call.engine)
		try:
			await taskFunction(iface)
		except asyncio.CancelledError as e:
			raise asyncio.CancelledError
		except Exception as e:
			print("Unhandled exception in call handler:", e)
			pass

	task = loop.create_task(call_func(call))

	text = ""
	limiter = RateLimiter(100_000_000)
	while not task.done():
		try:
			loop.run_until_complete(asyncio.sleep(0.001))
			if limiter.check():
				screen.clear()
				screen.move(0,0)
				screen.addstr(text)
			try:
				key = screen.getkey()
				if key in "1234567890#*":
					text = "pressed "+key
					call.dtmf.onDtmfDigit(key)
			except Exception as e:
				pass
			# todo: get keypad input here and send it into call.dtmf
		except KeyboardInterrupt:
			task.cancel()

	call.hangup()
	task.cancel()
	loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
	loop.close()

def runVoipClient(taskFunction, port=None):
	curses.wrapper(lambda x,taskFunction=taskFunction:runVoipClientReal(x, taskFunction))
