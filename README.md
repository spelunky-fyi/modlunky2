[![PyPi Version](https://img.shields.io/pypi/v/modlunky2.svg)](https://pypi.python.org/pypi/modlunky2/)

# modlunky2

Repository for modding interface for Spelunky 2.

## Installation

You'll need to have [Python 3.7 or 3.8](https://www.python.org/downloads/) installed to install these tools. Make sure when you're installing Python that you click the checkbox to add Python to your `PATH`:

![Add Python to PATH](https://cdn.discordapp.com/attachments/756241793753809106/771016197424152576/0001_add_Python_to_Path.png).

If you've already installed Python without doing this you can either re-install or follow the instructions at this site: https://datatofish.com/add-python-to-windows-path/

Once you have python installed you can open `cmd` and run the following:

```console
pip install --upgrade modlunky2
```

> :warning: This currently only works on version 1.14+ of Spelunky 2.

Once installed you should have a command called `modlunky2`.


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
> python setup.py develop
```

This will install any dependencies as well as setting up links on your path to your local source files. Once this is done
you'll be able to execute the binaries right from your path after any changes to the source without the need to build or
install anything. If you add new source files you may have to run `python setup.py develop` again to make sure they're linked.
