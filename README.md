[![PyPi Version](https://img.shields.io/pypi/v/modlunky2.svg)](https://pypi.python.org/pypi/modlunky2/)

# modlunky2

Modlunky 2 is a tool for creating and using mods related to Spelunky 2.

## Installation

[Download the latest version](https://github.com/spelunky-fyi/modlunky2/releases) of modlunky2.exe to your Spelunky 2 installation directory.

## Usage

Follow the instructions in the [Modlunky 2 Wiki](https://github.com/spelunky-fyi/modlunky2/wiki).

## Disclaimer
You are strongly discouraged from using any modding tools in your actual online Steam installation as to prevent unlocking achievements, corrupting your savefile and cheating in the leaderboards.

You can make a copy of your game somewhere else and install [Mr. Goldbergs Steam Emulator](https://gitlab.com/Mr_Goldberg/goldberg_emulator/-/releases) in the game directory. (TL;DR: Copy the steam_api64.dll from the zip to the offline game directory and create steam_appid.txt with the text `418530` in it.) Also block the modded installation in your firewall.

If you break anything using this tool you get to keep both pieces. Do not report modding related bugs to Blitworks.

## Development

If you'd like to contribute to `modlunky2` here are some steps to setup your environment.

### VirtualEnv

*While not required, a virtualenv is a nice way to keep this projects dependencies isolated from the rest of your system. This step is optional but recommended*

In the root directory you can make a virtualenv. It will be excluded from commits by default

```console
python -m venv venv
```
Whenever developing the project you'll want to activate the virtualenv in your terminal. This is platform dependent and there are more comprehensive docs available here: https://docs.python.org/3/library/venv.html

> :warning: If you're using PowerShell on Windows you might need to run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`. More information on execution policy is available in the link above.

| Platform | Shell           | Command to activate virtual environment |
|----------|-----------------|-----------------------------------------|
| POSIX    | bash/zsh        | $ source <venv>/bin/activate            |
|          | fish            | $ source <venv>/bin/activate.fish       |
|          | csh/tcsh        | $ source <venv>/bin/activate.csh        |
|          | PowerShell Core | $ <venv>/bin/Activate.ps1               |
| Windows  | cmd.exe         | C:\> <venv>\Scripts\activate.bat        |
|          | PowerShell      | PS C:\> <venv>\Scripts\Activate.ps1     |


### Setup

Once you have your virtual environment setup and activated you'll want to finish setting up the development environment.

```console
> pip install -r requirements.txt
> pip install -r requirements-dev.txt
> python setup.py develop
```

This will install any dependencies as well as setting up links on your path to your local source files. Once this is done
you'll be able to execute the binaries right from your path after any changes to the source without the need to build or
install anything. If you add new source files you may have to run `python setup.py develop` again to make sure they're linked.

### Running Locally

```
modlunky2
```

### Building Distributions

#### PyPI
```
python setup.py sdist
python -m twine upload .\dist\modlunky2-$VERSION.tar.gz
```

#### EXE

The default pyinstaller from pip seems prone to false detection from antivirus
so you need to build your own version per https://pyinstaller.readthedocs.io/en/stable/bootloader-building.html

See: https://stackoverflow.com/a/52054580

##### Build
```
python build-exe.py
```

## Contributors

Special thanks to the following contributors for helping make modlunky possible:

* `garebear`
* `SciresM`
* `Cloppershy`
* `iojonmbnmb`
* `Dregu`
* `JackHasWifi`
* `mriswithe`
* `Malacath`