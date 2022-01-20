# Contributing to modlunky2

## Discussion

Most discussion occurs in the [Spelunky Community Discord server](https://discord.gg/spelunky-community)

* `#s2-modding-help` — Get help with using or making mods
* `#s2-modding-tooldevs` — Discuss development, e.g. bug fixes or implementing new features

## Bugs

Before reporting a bug, please check the [existing ones](https://github.com/spelunky-fyi/modlunky2/issues)
to see whether yours has already been reported.

## Development

### Setup

Before making substantial changes to Modlunky2, please discuss them in `#s2-modding-tooldevs`

#### Python virtualenv

A virtualenv is a nice way to keep this project's dependencies isolated from the rest of your  system.
This step is optional but recommended

In the root directory you can make a virtualenv. It will be excluded from commits by default

```console
python -m venv venv
```

Whenever developing the project you'll want to activate the [virtualenv](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment)
in your terminal. This is platform dependent

> :warning: If you're using PowerShell on Windows you might need to run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

| Platform | Shell           | Command to activate virtual environment |
|----------|-----------------|-----------------------------------------|
| Windows  | cmd.exe         | `<venv>\Scripts\activate.bat`           |
|          | PowerShell      | `<venv>\Scripts\Activate.ps1`           |
| POSIX    | bash/zsh        | `source <venv>/bin/activate`            |
|          | fish            | `source <venv>/bin/activate.fish`       |
|          | csh/tcsh        | `source <venv>/bin/activate.csh`        |
|          | PowerShell Core | `<venv>/bin/Activate.ps1`               |

#### Python packages

Once you have your virtual environment setup and activated, you'll want to finish setting up the
development environment.

```console
pip install --upgrade -r requirements.txt -r requirements-dev.txt -r requirements-win.txt
python setup.py develop
```

This will install any dependencies as well as setting up links on your path to your local source files.

### Running

You can simply run Modlunky2 in a console via

```console
modlunky2
```

If the command is not found, you may have forgotten to activate the virtualenv.

### IDE

[VS Code](https://code.visualstudio.com/) is the most common IDE used for Modlunky2 development.
You'll need the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python).
A settings.json file is included with common settings.

### Building `modlunky2.exe`

> :warning: This usually isn't needed for development, just releases.

#### GitHub

If your code is in `main` branch (or a PR for it), you can download the exe from
[GitHub actions](https://github.com/spelunky-fyi/modlunky2/actions/workflows/build-exe.yml).

#### Local build

You need to [install Rust](https://www.rust-lang.org/tools/install). We use it to bootstrap the Python application.

To build the exe, run

```console
python build-exe.py
```

Once its done, it will open the folder `src/launcher/target/release/` which contains `modlunky2.exe`

#### Troubleshooting

##### Pyinstaller

The default pyinstaller from pip is usually fine.

If `modlunky2.exe` is being removed by antivirus, [building your own](https://pyinstaller.readthedocs.io/en/stable/bootloader-building.html) might help.

##### Audio DLLs

The `dll`'s to extract audio are included in the `dist` directory. These are used to extract files from the FSB soundbank.

If updated versions are needed, they can be obtained from [python-fsb5](https://github.com/HearthSim/python-fsb5/releases).
Put the `libogg.dll` and `libvorbis.dll` files from `python-fsb5_win64.zip` into the `dist` directory.
