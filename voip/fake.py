import pyaudio
import asyncio
import time
from .pcm import floatToPacked, packedToFloat
from .engine import AudioEngine
from .dtmf import DTMF
from .iface import CallInterface
import curses
from contextlib import redirect_stdout

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

class CursesPrinter():
	def __init__(self, screen):
		self.screen = screen
		self.height, self.width = self.screen.getmaxyx()
		self.text = ""
		self.textupdated = False
		self.limiter = RateLimiter(100_000_000)
		self.frame = None

	def write(self, data):
		self.text += data
		self.textupdated = True

	def close(self):
		pass

	def flush(self):
		pass

	def setFrame(self, frame):
		self.frame = frame

	def commit(self, force=False):
		if self.limiter.check() or force:
			oldheight = self.height
			self.height, self.width = self.screen.getmaxyx()
			if self.height != oldheight or self.textupdated:
				self.text = "\n".join(self.text.split("\n")[-self.height:])
				self.textupdated = False
			self.screen.clear()
			self.screen.move(0,0)
			try:
				self.screen.addstr(self.text)
			except Exception:
				pass
			if self.frame is not None:
				self.screen.move(11,0)
				self.screen.addstr(str(self.frame))


def runVoipClientReal(printer, screen, taskFunction):
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
	print("Call started")

	while not task.done():
		try:
			loop.run_until_complete(asyncio.sleep(0.001))
			printer.commit()
			try:
				key = screen.getkey()
				if key in "1234567890#*":
					print("User pressed "+key)
					call.dtmf.onDtmfDigit(key)
			except Exception as e:
				pass
			# todo: get keypad input here and send it into call.dtmf
		except KeyboardInterrupt:
			print("Cancelling call due to keyboard interrupt")
			task.cancel()

	print("Call ended")
	call.hangup()
	task.cancel()
	loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
	loop.close()
	print("Press any key to quit")
	printer.commit(force=True)
	try:
		screen.nodelay(False)
		key = screen.getkey()
	except KeyboardInterrupt:
		pass

def runVoipClientCurses(screen, taskFunction):
	screen.nodelay(True)
	printer = CursesPrinter(screen)

	with redirect_stdout(printer):
		runVoipClientReal(printer, screen, taskFunction)

def runVoipClient(taskFunction, port=None):
	curses.wrapper(lambda x,taskFunction=taskFunction:runVoipClientCurses(x, taskFunction))
