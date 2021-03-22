# -*- coding: UTF-8 -*-

import os
from six import PY2
from kodi_six import xbmcgui
from resources.lib.modules import control

def get():
    changelogfile = os.path.join(control.addonPath, 'changelog.txt')
    if PY2:
        from io import open as io_open
        r = io_open(changelogfile, 'r', encoding='utf-8')
    else:
        r = open(changelogfile, 'r', encoding='utf-8')
    text = r.read()
    r.close()
    id = 10147
    control.execute('ActivateWindow(%d)' % id)
    control.sleep(500)
    win = xbmcgui.Window(id)
    retry = 50
    while (retry > 0):
        try:
            control.sleep(10)
            retry -= 1
            win.getControl(1).setLabel('[COLOR gold]TheOath [/COLOR] --Changelog--')
            win.getControl(5).setText(text)
            return
        except:
            pass

