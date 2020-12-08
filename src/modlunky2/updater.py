import os
import subprocess
import time
import urllib.request
from shutil import copyfile


def main():
    cwd = os.getcwd()

    copyfile(cwd + "/modlunky2.exe", cwd + "/modlunky2.exe.bak")  # Creates temp backup

    try:
        os.remove(cwd + "/modlunky2.exe")  # deletes current version
        print("Download latest release of Modlunky2..")
        # downlaods latest release on github
        url = "https://github.com/spelunky-fyi/modlunky2/releases/latest/download/modlunky2.exe"
        urllib.request.urlretrieve(url, cwd + "/modlunky2.exe")

        print("Download Complete!")
        # deletes backup once download is complete
        os.remove(cwd + "/modlunky2.exe.bak")

        # runs tool again and closes
        subprocess.call([cwd + "/modlunky2.exe"])

        # Wait for 5 seconds to give tool time to reopen
        time.sleep(5)
    except OSError:
        # restores backup if download failed for whatever reason
        copyfile(cwd + "/modlunky2.exe.bak", cwd + "modlunky2.exe")
        print("Download Failed.")


if __name__ == "__main__":
    main()
