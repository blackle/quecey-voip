## Quecey's VOIP Library

This is a framework for making sip voice services like phone trees, synthesizers, sstv generators, and other experiments.

### Setup

Here's the steps to getting a development environment setup. I used debian.

#### Dependencies

General deps:
```sh
sudo apt install build-essential git python3-dev swig libopus-dev libssl-dev libsdl2-dev
```

Pjsip
```sh
# using my branch because it adds a dtmf keypad to the python sample
git clone https://github.com/blackle/pjproject.git
cd pjproject
git checkout blackle
# you can use a local --prefix to install locally
./configure --enable-shared --prefix=/usr
make dep
make
# don't use sudo make install if you set a --prefix, just "make install"
sudo make install
```

Pjsip python SWIG bindings
```sh
# in pjproject
cd pjsip-apps/src/swig/python
make
make install
```

Check that the install worked:
```sh
# if you are using a local --prefix, you need to set LD_LIBRARY_PATH=your_prefix/lib
python3 -c "import pjsua2"
```

#### Cloning this repo

```sh
git clone https://github.com/blackle/quecey-voip.git
cd quecey-voip
```

Run a sample app with:

```sh
# use LD_LIBRARY_PATH if you installed pjproject to a --prefix
./test.py
```

Keep this running while we go on to the next step.

#### Using PJSIP's call software

```sh
sudo apt install python3-tk
cd pjproject/pjsip-apps/src/pygui
# use LD_LIBRARY_PATH if you installed pjproject to a --prefix
python3 ./application.py
```

Go to `file -> add account` and fill in the following details:

```
ID (URI) = sip:test
```

After creating the account, it should list itself as "doesn't register."

Next, add a "buddy" by right clicking on the account. Set its URI to `sip:localhost:5060`

Right click on the buddy to start the audio call. You should hear a list of tones in order. Type "1234" into the keypad after the tones to hear "password correct."

### API Documentation

Everything relevant to handling a call is in the "voip" module. The runVoipClient function starts a new SIP client that uses a provided async function to deal with incoming calls. To end a call, simply return from the handler function early, or raise an unhandled exception.

#### Simple "Hello World"

Make a new file in this repo called "hello.py" and fill it with the following code:

```py
#!/usr/bin/env python3
from voip import runVoipClient

async def handler(call):
	await call.playTone(420, .5)
	await call.playTone(560, .5)
	await call.playTone(650, .5)

if __name__ == "__main__":
	runVoipClient(handler)
```

The crux of this example is that when a new phone call comes in, your "handler" function will be called with a "call" object. This call object provides many methods, some of which are async (and therefore require you to "await" them) and some of which are not.

Run this with the LD_LIBRARY_PATH environment variable set if you used a custom --prefix to install PJSIP.

You can now call this application using PJSIP's call software, like how you did in the previous section. You should hear three tones in order.

#### Playing a custom sound

To play a custom sound, first you need to convert it to a 16-bit, 8000Hz WAV. You can use sox for this

```sh
sox -V my_sound.mp3 -r 8000 -c 1 -t wav my_sound.wav
```

Place my_sound.wav in the "assets" folder of this directory. If you plan to make a lot, make a subdirectory with a unique name.

We can load our sound with loadWAVtoPCM, then play our sound using the playPCM method on the call object:

```py
#!/usr/bin/env python3
from voip import runVoipClient, loadWAVtoPCM

my_sound = loadWAVtoPCM("assets/my_sound.wav")

async def handler(call):
	await call.playPCM(my_sound)

if __name__ == "__main__":
	runVoipClient(handler)
```

The playPCM method takes a list of floats in the range [-1, 1] which represent the amplitude of the sound at 8000Hz. You can generate your own lists to play custom sounds, or use the playCustom method which will be covered later.

#### Getting keypad input

When a user presses a button on the keypad of their phone, it generates something called a "DTMF tone." These tones encode the particular key that was pressed. You can use the "getDTMF" method to get those keys.

```py
async def handler(call):
	# play a tone to signal to the user that we're accepting keypad input
	await call.playTone(1000, .25)
	key = await call.getDTMF()
	print(key)
```

This example will print out the key pressed, then end the call.

The getDTMF method has two option parameters. `n` allows you to specify how many keys to wait for, and `filter` allows you to specify a list of allowed keys. In the following example, we'll wait for 4 numeric digits.

```py
async def handler(call):
	await call.playTone(1000, .25)
	keys = await call.getDTMF(n=4, filter="1234567890")
	print(keys)
```

We can add a timeout by wrapping it in `asyncio.wait_for`. If the timeout triggers, it raises a TimeoutError. Be sure to import asyncio for this example to work.

```py
async def handler(call):
	await call.playTone(1000, .25)
	try:
		# wait for 4 numbers for max 60 seconds
		keys = await asyncio.wait_for(call.getDTMF(n=4, filter="1234567890"), 60)
	except TimeoutError:
		keys = "not enough keys pressed in the alloted time"
	print(keys)
```

#### Recording audio

The call object has a "recordPCM" method. This returns a future which resolves to a list of floats, in the same format that playPCM expects. However, if you simply "await" on the method, it will never finish because it doesn't know how long it should record for.

To manage the duration of the recording, you need to import the RecordController object from the voip module. By passing an instance of it to recordPCM, you can stop the recording at any time by calling the stop method on the RecordController. Here is an example of recording audio until we get a DTMF key:

```py
from voip import runVoipClient, RecordController

async def handler(call):
	await call.playTone(1000, .25)
	# the RecordController lets us control when the recording should stop
	controller = RecordController()
	# start recording
	recorder = call.recordPCM(controller)
	# wait for a keypress
	key = call.getDTMF()
	# stop recording
	controller.stop()
	# get the recording
	recording = await recorder
	# play it back
	await call.playPCM(recording)
```

#### Custom playback/recording methods

Sometimes you want to playback audio that you generate in realtime, or process incoming sounds one sample at a time. For example you might have some code that generates a song given the time. Another example is encoding the incoming audio with some codec for compression. For those usecases you'll want to use the playCustom or recordCustom methods on the call object.

Below is the source code for an echo client. This client recieves samples from recordCustom, adds them to a queue, which are then played using playCustom

```py
async def handler(call):
	sampleQueue = queue.Queue(maxsize=8000*2)
	stop = False
	def sampleInput(sample):
		# sample is the incoming audio sample
		if stop:
			# returning False stops the recording
			return False
		if not sampleQueue.full():
			# put the recieved sample into the queue
			sampleQueue.put(sample)
		# returning true continues the recording so this 
		# method will be called for the next incoming sample
		return True
	def sampleOutput(t, delta):
		# t is the time in seconds since playback started
		# delta is the time in seconds between subsequent calls
		if stop:
			# returning None stops the playback
			return None
		if sampleQueue.qsize() < 160:
			# return 0 if there aren't enough samples in the queue
			return 0
		# this pops the sample off the queue and returns it for playback
		return sampleQueue.get()
	# recordCustom takes a function that gets
	# called for each incoming audio sample
	call.recordCustom(sampleInput)
	# playCustom takes a function that gets called
	# every time a sample needs to be played
	call.playCustom(sampleOutput)
	# wait for a keypress
	await call.getDTMF()
```

#### Cancelling playback

One thing that one might want to do is play a sound but then do other things in the background. Here is an example:

```py
def handler(call):
	playback = call.playPCM(my_sound)
	# wait for a keypress
	key = await call.getDTMF()
	# once we get it, cancel the playing sound
	playback.cancel()
	if key == '1':
		await do_thing_for_one(call)
	else:
		await do_thing_for_other(call)
```