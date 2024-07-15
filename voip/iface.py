
def delegate_method(delegate_to, method_name):
	def wrapper(self, *args, **kwargs):
		delegate = getattr(self, delegate_to)
		method = getattr(delegate, method_name)
		return method(*args, **kwargs)
	return wrapper

class CallInterface:
	def __init__(self, call, dtmf, engine):
		self.call = call
		self.dtmf = dtmf
		self.engine = engine

	getDTMF = delegate_method("dtmf", "getDTMF")
	playPCM = delegate_method("engine", "playPCM")
	playTone = delegate_method("engine", "playTone")
	playCustom = delegate_method("engine", "playCustom")
	recordPCM = delegate_method("engine", "recordPCM")
	recordCustom = delegate_method("engine", "recordCustom")

	def getRemoteUri(self):
		return self.call.remoteUri