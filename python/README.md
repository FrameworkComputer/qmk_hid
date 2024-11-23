# Python

## Installing

Pre-requisites: Python with pip

```sh
python3 -m pip install qmk_hid
```

## GUI

On Linux install Python requirements via `python3 -m pip install -r requirements.txt` and run `python3 qmk_hid/gui.py`.
On Windows download the `qmk_gui.exe` and run it.

## Developing

One time setup

```
# Install dependencies on Ubuntu
sudo apt install python3 python3-tk python3-devel libhidapi-dev
# Install dependencies on Fedora
sudo dnf install python3 python3-tkinter hidapi-devel
# Create local venv and enter it
python3 -m venv venv
source venv/bin/activate
# Install package into local env
python3 -m pip install -e .
```

Developing

```
# In every new shell, source the virtual environment
source venv/bin/activate
# Launch GUI or commandline
qmk_gui

# Launch Python REPL and import the library
# As example, launch the GUI
> python3
>>> from qmk_hid import gui
>>> gui.main()
```
