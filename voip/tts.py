import subprocess
import io
from .pcm import loadWAVtoPCM

def TTStoPCM(text, opts=[]):
	process = subprocess.run(["espeak", "--stdout", *opts, text], stdout=subprocess.PIPE, timeout=1)
	data = process.stdout
	return loadWAVtoPCM(io.BytesIO(data))
