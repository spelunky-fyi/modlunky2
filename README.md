[![PyPi Version](https://img.shields.io/pypi/v/modlunky2.svg)](https://pypi.python.org/pypi/modlunky2/)

# modlunky2

Repository for modding interface for Spelunky 2.

# Credits

Special thanks to  `SciresM`, `Cloppershy`, `iojonmbnmb`, and `Dregu` for all of the help
in making this tool a reality.

## Installation

Grabbed the latest release from https://github.com/spelunky-fyi/modlunky2/releases . Copy the modlunky2.exe to your
Spelunky 2 installation directory and run it. A terminal will appear with a link to webpage. It should be
http://127.0.0.1:8040/ . Leave this running while you're using the modding UI.

## Disclaimer
You are strongly discouraged from using any modding tools in your actual online Steam installation as to prevent unlocking achievements, corrupting your savefile and cheating in the leaderboards. You should make a copy of your game somewhere else and install [Mr. Goldbergs Steam Emulator](https://gitlab.com/Mr_Goldberg/goldberg_emulator/-/releases) in the game directory. (TL;DR: Copy the steam_api64.dll from the zip to the offline game directory and create steam_appid.txt with the text `418530` in it.) Also block the modded installation in your firewall. If you break anything using this tool you get to keep both pieces. Do not report modding related bugs to Blitworks.

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
> git clone https://github.com/spelunky-fyi/modlunky2/
> cd modlunky2
> pip install -r requirements.txt
> python setup.py develop
```

This will install any dependencies as well as setting up links on your path to your local source files. Once this is done
you'll be able to execute the binaries right from your path after any changes to the source without the need to build or
install anything. If you add new source files you may have to run `python setup.py develop` again to make sure they're linked.

### Running Locally

```
modlunky2 --install-dir="C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2"
```

### Building Distributions

#### PyPI
```
python setup.py sdist
python -m twine upload .\dist\modlunky2-$VERSION.tar.gz
```

#### EXE
```
pyinstaller.exe --clean .\pyinstaller-cli.py --add-data "VERSION;." --add-data "src/modlunky2/static;static" --name modlunky2 --onefile --noconsole --icon=.\src\modlunky2\static\images\icon.ico
```
