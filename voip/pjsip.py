import pjsua2 as pj
import time
import math
import asyncio
import os
from .pcm import floatToPacked, packedToFloat
from .engine import AudioEngine

class AudioMediaPort(pj.AudioMediaPort):
	def __init__(self, fmt):
		pj.AudioMediaPort.__init__(self)
		samplesPerFrame = (fmt.clockRate * fmt.frameTimeUsec) // 1000000
		clockRate = fmt.clockRate
		frameNsec = fmt.frameTimeUsec * 1000
		self.engine = AudioEngine(samplesPerFrame, clockRate, frameNsec)

	def onFrameRequested(self, frame):
		samples = self.engine.onFrameRequested()

		if samples is None:
			return

		frame.type = pj.PJMEDIA_TYPE_AUDIO
		for x in samples:
			low, hi = floatToPacked(x)
			frame.buf.append(low)
			frame.buf.append(hi)

	def onFrameReceived(self, frame):
		samples = []
		for i in range(frame.buf.size()):
			if i % 2 == 1:
				x = packedToFloat(frame.buf[i], frame.buf[i-1])
				samples.append(x)

		self.engine.onFrameReceived(samples)

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
	def __init__(self, dtmf, engine):
		self.dtmf = call
		self.engine = engine

	getDTMF = delegate_method("dtmf", "getDTMF")
	playPCM = delegate_method("engine", "playPCM")
	playTone = delegate_method("engine", "playTone")
	playCustom = delegate_method("engine", "playCustom")
	recordPCM = delegate_method("engine", "recordPCM")
	recordCustom = delegate_method("engine", "recordCustom")

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
					async def call_func(call):
						iface = CallInterface(call, call.port.engine)
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
					call.task = loop.create_task(call_func(call))
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
