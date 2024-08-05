# make-a-fish

## Setup

If you have system wide pip, you can simply run

```sh
pip3 install -r requirements.txt
```

If you have issues such as pip asking you to use your system package manager, you can make a virtual environment

```sh
# At the root of the repo
cd (wherever)/quecey-voip
# Creates a virtual environment.
python3 -m venv .venv
.venv/bin/pip install -m make-a-fish/requirements.txt

# And run using the venv python
.venv/bin/python3 main.py
```
