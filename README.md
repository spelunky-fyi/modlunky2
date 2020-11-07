[![PyPi Version](https://img.shields.io/pypi/v/modlunky2.svg)](https://pypi.python.org/pypi/modlunky2/)

# modlunky2

Repository for modding interface for Spelunky 2.

## Installation

Grabbed the latest release from https://github.com/spelunky-fyi/modlunky2/releases . Copy the modlunky2.exe to your
Spelunky 2 installation directory and run it. A terminal will appear with a link to webpage. It should be
http://127.0.0.1:8040/ . Leave this running while you're using the modding UI.


## Development

If you'd like to contribute to `modlunky2` here are some steps to setup your environment.

### Creating VirtualEnv
In the root directory you can make a virtualenv. It will be excluded from commits by default
```console
> python -m venv venv
```

### Activate VirtualEnv

You'll want to activate the virtual environment whenever you're testing any commands from this package

#### Powershell
```console
> venv\Scripts\activate.bat
```

#### cmd
```console
> venv/Scripts/Activate.ps1
```

#### bash/zsh
```console
> source venv/bin/activate
```

### Setup

Once you have your virtual environment setup and activated you'll want to finish setting up the development environment.

```console
> pip install -r requirements.txt
> python setup.py develop
```

This will install any dependencies as well as setting up links on your path to your local source files. Once this is done
you'll be able to execute the binaries right from your path after any changes to the source without the need to build or
install anything. If you add new source files you may have to run `python setup.py develop` again to make sure they're linked.

### Running Locally

```
modlunky2 --install-dir="C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2" --debug
```

### Building Distributions

#### PyPI
```
python setup.py sdist
python -m twine upload .\dist\modlunky2-$VERSION.tar.gz
```

#### EXE
```
pyinstaller modlunky2.spec
```