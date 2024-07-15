import pjsua2 as pj
import time
import math
import asyncio
import os
from .pcm import floatToPacked, packedToFloat

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

class AudioMediaPort(pj.AudioMediaPort):
	def __init__(self, fmt):
		pj.AudioMediaPort.__init__(self)
		self.time = 0
		self.samplesPerFrame = (fmt.clockRate * fmt.frameTimeUsec) // 1000000
		self.clockRate = fmt.clockRate
		self.playTasks = []
		self.recordTasks = []
		self.nextDeadline = None
		self.frameNsec = fmt.frameTimeUsec * 1000

	def playPCM(self, pcm, loop=False):
		future = asyncio.Future()
		self.playTasks.append(AudioPlaybackTask(future, pcm, loop))
		return future

	def playCustom(self, func):
		future = asyncio.Future()
		self.playTasks.append(AudioPlaybackCustomTask(future, func, self.clockRate))
		return future

	def playTone(self, pitch, duration):
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

	def onFrameRequested(self, frame):
		now = time.time_ns()
		if self.nextDeadline is not None:
			if now < self.nextDeadline:
				return
		else:
			self.nextDeadline = now
		self.nextDeadline += self.frameNsec

		frame.type = pj.PJMEDIA_TYPE_AUDIO
		for i in range(self.samplesPerFrame):
			x = 0
			for task in self.playTasks:
				x += task.getSample()

			x = min(max(-1,x),1)

			low, hi = floatToPacked(x)
			frame.buf.append(low)
			frame.buf.append(hi)

		self.playTasks = [task for task in self.playTasks if not task.future.done()]

	def onFrameReceived(self, frame):
		if len(self.recordTasks) == 0:
			return

		for i in range(frame.buf.size()):
			if i % 2 == 1:
				x = packedToFloat(frame.buf[i], frame.buf[i-1])
				for task in self.recordTasks:
					task.addSample(x)

		self.recordTasks = [task for task in self.recordTasks if not task.future.done()]

def genAudio(t, delta):
	if t > .1:
		return None
	return math.sin(t * 440 * math.pi * 2)

class Call(pj.Call):
	def __init__(self, acc, call_id=pj.PJSUA_INVALID_ID):
		pj.Call.__init__(self, acc, call_id)
		self.acc = acc

		fmt = pj.MediaFormatAudio()
		fmt.type = pj.PJMEDIA_TYPE_AUDIO
		fmt.clockRate = 8000
		fmt.channelCount = 1
		fmt.bitsPerSample = 16
		fmt.frameTimeUsec = 20000
		self.port = AudioMediaPort(fmt)
		self.port.createPort("port", fmt)

		self.remoteUri = "\"UNKNOWN\" <sip:unknown@localhost>"

		self.future = None
		self.task = None #todo: cancel task on call hangup

	def onCallState(self, prm):
		ci = self.getInfo()
		self.remoteUri = ci.remoteUri
		print("onCallState", self.remoteUri)
		if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
			if self.task is not None:
				self.task.cancel()
				self.task = None
		self.acc.updateCallState(self, ci)

	def onCallMediaState(self, prm):
		ci = self.getInfo()
		for mi in ci.media:
			if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
				m = self.getMedia(mi.index)
				am = pj.AudioMedia.typecastFromMedia(m)
				self.port.startTransmit(am)
				am.startTransmit(self.port)

	def getDTMF(self, n=1, filter=None):
		if self.future and not self.future.done():
			raise Exception("getDTMF already called and not resolved")
		self.future = asyncio.Future()
		self.digitsToGet = n
		self.digitsFilter = filter
		self.digits = []
		return self.future

	def onDtmfDigit(self, prm):
		if self.future and not self.future.done():
			if self.digitsFilter is not None and prm.digit not in self.digitsFilter:
				return
			self.digits.append(prm.digit)
			if len(self.digits) >= self.digitsToGet:
				self.future.set_result("".join(self.digits))
				self.future = None

def delegate_method(delegate_to, method_name):
	def wrapper(self, *args, **kwargs):
		delegate = getattr(self, delegate_to)
		method = getattr(delegate, method_name)
		return method(*args, **kwargs)
	return wrapper

class CallInterface:
	def __init__(self, call, port):
		self.call = call
		self.port = port

	getDTMF = delegate_method("call", "getDTMF")
	playPCM = delegate_method("port", "playPCM")
	playTone = delegate_method("port", "playTone")
	playCustom = delegate_method("port", "playCustom")
	recordPCM = delegate_method("port", "recordPCM")
	recordCustom = delegate_method("port", "recordCustom")

	def getRemoteUri(self):
		return self.call.remoteUri

class Account(pj.Account):
	def __init__(self, ep):
		pj.Account.__init__(self)
		self.calls = set()
		self.ep = ep

	def onIncomingCall(self, prm):
		print("Incoming call!")

		call = Call(self, call_id=prm.callId)
		self.calls.add(call)

		if 'IP_WHITELIST' in os.environ and prm.rdata.srcAddress != os.environ['IP_WHITELIST']:
			print("rejecting call")
			call_prm = pj.CallOpParam()
			call_prm.statusCode = 403
			call.hangup(call_prm)
			return

		call_prm = pj.CallOpParam()
		call_prm.statusCode = 200
		call.answer(call_prm)

	def updateCallState(self, call, ci):
		if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
			self.calls.remove(call)
			print("Call removed.")
			call.__disown__()

def runVoipClient(taskFunction, port=None):
	if port is None: port = 5060

	ep_cfg = pj.EpConfig()

	ep_cfg.logConfig.level = 0
	ep_cfg.logConfig.consoleLevel = 0
	ep_cfg.logConfig.msgLogging = False

	ep_cfg.uaConfig.maxCalls = 1

	ep_cfg.medConfig.clockRate = 8000
	ep_cfg.medConfig.channelCount = 1
	ep_cfg.medConfig.audioFramePtime = 10

	ep = pj.Endpoint()
	ep.libCreate()
	ep.libInit(ep_cfg)

	# Create SIP transport. Error handling sample is shown
	sipTpConfig = pj.TransportConfig()
	sipTpConfig.port = port
	ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sipTpConfig)
	# Start the library
	ep.libStart()

	acfg = pj.AccountConfig()
	acfg.idUri = "sip:quecey"
	# Create the account
	acc = Account(ep)
	acc.create(acfg)
	# Here we don't have anything else to do..
	loop = asyncio.get_event_loop()

	while True:
		try:
			loop.run_until_complete(asyncio.sleep(0.1))
			calls = list(acc.calls)
			for call in calls:
				if call.task is None:
					async def call_func(call, port):
						iface = CallInterface(call, call.port)
						try:
							await taskFunction(iface)
						except asyncio.CancelledError as e:
							return
						except Exception as e:
							print("Unhandled exception in call handler:", e)
							pass
						call.task = None
						if call.isActive():
							call_prm = pj.CallOpParam()
							call_prm.statusCode = 200
							call.hangup(call_prm)
					call.task = loop.create_task(call_func(call, call.port))
		except KeyboardInterrupt:
			break

	calls = list(acc.calls)
	for call in calls:
		if call.isActive():
			call_prm = pj.CallOpParam()
			call_prm.statusCode = 200
			call.hangup(call_prm)
	calls = None

	loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))

	loop.close()
	acc = None

	# Destroy the library
	ep.libDestroy()
	ep = None
