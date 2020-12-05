import urllib.request
from shutil import copyfile
import os

cwd = os.getcwd()

copyfile(cwd + '/modlunky2.exe', cwd + '/modlunky2.exe.bak') #Creates temp backup

try:
    os.remove(cwd + '/modlunky2.exe') # deletes current version
    print('Download latest release of Modlunky2..')
    url = "https://github.com/spelunky-fyi/modlunky2/releases/latest/download/modlunky2.exe" #downlaods latest release on github
    urllib.request.urlretrieve(url, cwd + '/modlunky2.exe')

    print('Download Complete!')
    os.remove(cwd + '/modlunky2.exe.bak') # deletes backup once download is complete

    import subprocess
    subprocess.call([cwd + '/modlunky2.exe']) # runs tool again and closes
    import time
    time.sleep(5)# Wait for 5 seconds to give tool time to reopen
except OSError:
    copyfile(cwd + '/modlunky2.exe.bak', cwd + 'modlunky2.exe') # restores backup if download failed for whatever reason
    print('Download Failed.')
