import struct
import wave

def normalizePCM(pcm):
	"""Helper function to normalize volume and trim silence on either end"""
	try:
		start = next(i for i, x in enumerate(pcm) if abs(x) > .005)
		end = next(len(pcm)-i-1 for i, x in enumerate(pcm[::-1]) if abs(x) > .005)
		m = max(abs(x) for x in pcm)
		return [x / m for x in pcm[start:end]]
	except:
		return []

def packedToFloat(a, b):
	x = a << 8 | b
	x = struct.unpack('<h', struct.pack('<H', x))[0]
	x /= 32767
	return x

def floatToPacked(x):
	x = int(x*32767)
	x = struct.unpack('<H', struct.pack('<h', x))[0]
	return (x & 0xff, (x & 0xff00) >> 8)

def resample(samples, to, fro):
	overflow = 0
	avg = 0
	count = 0
	resampled = []
	for i in range(len(samples)):
		overflow += fro/to
		if overflow > 1:
			overflow -= 1
			resampled.append(avg/count)
			avg = 0
			count = 0
		avg += samples[i]
		count += 1
	return resampled

def loadWAVtoPCM(filename):
	pcm = []
	with wave.open(filename, mode='rb') as w:
		rate = w.getframerate()
		assert(rate >= 8000)
		data = w.readframes(w.getnframes())
		for i in range(len(data)):
			if i % 2 == 1:
				pcm.append(packedToFloat(data[i], data[i-1]))
		if rate != 8000:
			pcm = resample(pcm, rate, 8000)

	return pcm

def savePCMtoWAV(pcm, filename):
	pcm_s16 = [int(x * 32767) for x in pcm]
	with wave.open(filename, mode='wb') as w:
		w.setparams([1, 2, 8000, len(pcm_s16), 'NONE', 'not compressed'])
		for sample in pcm_s16:
			w.writeframes(struct.pack('<h', sample))