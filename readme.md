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