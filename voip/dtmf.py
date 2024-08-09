import asyncio

class DTMF:
	def __init__(self):
		self.future = None

	def getDTMF(self, n=1, filter=None, on_first=None):
		if self.future and not self.future.done():
			raise Exception("getDTMF already called and not resolved")
		self.future = asyncio.Future()
		self.digitsToGet = n
		self.digitsFilter = filter
		self.digits = []
		self.on_first = on_first
		return self.future

	def onDtmfDigit(self, digit):
		if self.future and not self.future.done():
			if self.digitsFilter is not None and digit not in self.digitsFilter:
				return
			if self.on_first is not None and len(self.digits) == 0:
				self.on_first(digit)
			self.digits.append(digit)
			if len(self.digits) >= self.digitsToGet:
				self.future.set_result("".join(self.digits))
				self.future = None
				self.on_first = None
