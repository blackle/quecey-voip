#main audio engine stuff
import time
import math
import asyncio
import os

class RecordController:
	def __init__(self):
		self.stopped = False

	def stop(self):
		self.stopped = True

class AudioPlaybackTask:
	def __init__(self, future, pcm, loop):
		self.future = future
		self.t = 0
		self.pcm = pcm
		self.loop = loop

	def getSample(self):
		if self.future.done():
			return 0
		if self.t >= len(self.pcm):
			if not self.loop:
				self.future.set_result(True)
				return 0
			else:
				self.t = 0
		x = self.pcm[self.t]
		self.t += 1
		return x

class AudioPlaybackCustomTask:
	def __init__(self, future, func, clockRate):
		self.future = future
		self.t = 0
		self.func = func
		self.clockRate = clockRate

	def getSample(self):
		if self.future.done():
			return 0
		x = self.func(self.t / self.clockRate, 1 / self.clockRate)
		if x is None:
			self.future.set_result(True)
			return 0
		self.t += 1
		return x

class AudioRecordTask:
	def __init__(self, controller, future, maxlen):
		self.controller = controller
		self.future = future
		self.maxlen = maxlen
		self.pcm = []

	def addSample(self, x):
		if self.future.done():
			return
		self.pcm.append(x)
		if (self.maxlen and len(self.pcm) >= self.maxlen) or (self.controller and self.controller.stopped):
			self.future.set_result(self.pcm)

class AudioRecordCustomTask:
	def __init__(self, future, func):
		self.func = func
		self.future = future

	def addSample(self, x):
		if self.future.done():
			return
		if self.func(x) == False:
			self.future.set_result(True)

class AudioEngine():
	def __init__(self, samplesPerFrame, clockRate, frameNsec):
		self.samplesPerFrame = samplesPerFrame
		self.clockRate = clockRate
		self.frameNsec = frameNsec
		self.playTasks = []
		self.recordTasks = []
		self.nextDeadline = None

	def playPCM(self, pcm, loop=False):
		future = asyncio.Future()
		self.playTasks.append(AudioPlaybackTask(future, pcm, loop))
		return future

	def playCustom(self, func):
		future = asyncio.Future()
		self.playTasks.append(AudioPlaybackCustomTask(future, func, self.clockRate))
		return future

	def playTone(self, pitch, duration):
		print("playing tone")
		def toneFunc(t, delta):
			if t > duration:
				return None
			return math.sin(t * pitch * math.pi * 2)
		future = asyncio.Future()
		self.playTasks.append(AudioPlaybackCustomTask(future, toneFunc, self.clockRate))
		return future

	def recordPCM(self, controller=None, maxlen=None):
		if controller is None and maxlen is None:
			raise Exception("recordPCM called with no way to stop recording")
		future = asyncio.Future()
		self.recordTasks.append(AudioRecordTask(controller, future, maxlen))
		return future

	def recordCustom(self, func):
		future = asyncio.Future()
		self.recordTasks.append(AudioRecordCustomTask(future, func))
		return future

	def onFrameRequested(self):
		now = time.time_ns()
		if self.nextDeadline is not None:
			if now < self.nextDeadline:
				return None
		else:
			self.nextDeadline = now
		self.nextDeadline += self.frameNsec

		samples = []
		for i in range(self.samplesPerFrame):
			x = 0
			for task in self.playTasks:
				x += task.getSample()
			x = min(max(-1,x),1)
			samples.append(x)

		self.playTasks = [task for task in self.playTasks if not task.future.done()]
		return samples

	def onFrameReceived(self, samples):
		if len(self.recordTasks) == 0:
			return

		for x in samples:
			for task in self.recordTasks:
				task.addSample(x)

		self.recordTasks = [task for task in self.recordTasks if not task.future.done()]