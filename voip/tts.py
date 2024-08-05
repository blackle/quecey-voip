import subprocess
import io
from .pcm import loadWAVtoPCM

def TTStoPCM(text, opts=[], engine="espeak"):
	if engine == "espeak":
		process = subprocess.run(["espeak", "--stdout", *opts, text], stdout=subprocess.PIPE, timeout=1)
		data = process.stdout
		return loadWAVtoPCM(io.BytesIO(data))
	elif engine == "rhvoice":
		if opts == []:
			opts = ['-p', "bdl"]
		process = subprocess.run(["RHVoice-test", "-o", "/dev/stdout", *opts], input=text.encode('utf-8'), capture_output=True, timeout=1)
		data = process.stdout
		return loadWAVtoPCM(io.BytesIO(data))

