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
    head = '[COLOR gold]TheOath [/COLOR] --Changelog--'
    id = 10147
    control.execute('ActivateWindow(%d)' % id)
    control.sleep(500)
    win = xbmcgui.Window(id)
    win.getControl(1).setLabel(head)
    win.getControl(5).setText(text)

