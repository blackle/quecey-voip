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

#### Asterisk Install

Download the latest tar from https://www.asterisk.org/downloads/

```sh
sudo apt install libedit-dev uuid-dev libjansson-dev libxml2-dev libsqlite3-dev
tar -xzf ~/asterisk-20-current.tar.gz
cd asterisk-20.8.1
./configure
make menuconfig #go to "channel drivers" and enable chan_sip
make
sudo make install
```

Or you can install the `asterisk` package if you are on Ubuntu. Make sure to do `sudo systemctl disable asterisk.service` because we will be running it manually.

#### Asterisk config

Set the following files in /etc/asterisk/ to the supplied content:

sip.conf
```ini
[general]
context=public                  ; Default context for incoming calls. Defaults to 'default'
allowoverlap=no                 ; Disable overlap dialing support. (Default is yes)
udpbindaddr=0.0.0.0             ; IP address to bind UDP listen socket to (0.0.0.0 binds to all)
tcpenable=false                 ; Enable server for incoming TCP connections (default is no)
tcpbindaddr=0.0.0.0             ; IP address for TCP server to bind to (0.0.0.0 binds to all interfaces)
transport=tcp                   ; Set the default transports.  The order determines the primary default transport.
srvlookup=yes                   ; Enable DNS SRV lookups on outbound calls
qualify=yes

[authentication]

[experiment]
type=friend
secret=123456
host=dynamic
context=experiments
allow=alaw,ulaw,gsm,opus

[incoming]
type=friend
secret=123456
host=dynamic
context=experiments
allow=alaw,ulaw,gsm,opus
```

extensions.conf
```ini
[experiments]
exten => 1,1,Dial(SIP/experiment,10)
```

modules.conf
```ini
[modules]
autoload=yes
```

In a separate terminal, run asterisk:
```sh
sudo -i asterisk /usr/sbin/asterisk -fcvvv
```

#### Cloning this repo

```sh
git clone https://github.com/blackle/quecey-voip.git
cd quecey-voip
```

Edit the `run_with_creds.sh` script to replace all the instances of "blackle" with "experiment"

Run a sample app with:

```sh
# use LD_LIBRARY_PATH if you installed pjproject to a --prefix
./run_with_creds.sh ./voip.py
```

Keep this running while we go on to the next step.

#### Using PJSIP's call software

```sh
sudo apt install python3-tk
cd pjproject/pjsip-apps/src/pygui
python3 ./application.py
```

Go to `file -> add account` and fill in the following details:

```
ID (URI) = sip:incoming@localhost
Registrar (URI) = sip:localhost
Auth username = incoming
password = 123456
```

After creating the account, it should list itself as "registered." If not, make sure that asterisk is running.

Next, add a "buddy" by right clicking on the account. Set its URI to `sip:1@localhost`

Right click on the buddy to start the audio call. You should hear a list of tones in order.