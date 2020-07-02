# -*- coding: utf-8 -*-

"""
    Covenant Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import base64
import simplejson as json
import random
import re
import urllib

from resources.lib.modules import client
from resources.lib.modules import control


class trailer:
    def __init__(self):
        self.base_link = 'https://www.youtube.com'
        self.key = control.addon('plugin.video.youtube').getSetting('youtube.api.key')
        if self.key == '': self.key = base64.b64decode('QUl6YVN5QXc2VWtjREJpVk14ZXZxaGs3WE9la1BRU3dSaWNKaThR')
        try: self.key_link = '&key=%s' % self.key
        except: pass
        # self.key_link = random.choice(['QUl6YVN5QXc2VWtjREJpVk14ZXZxaGs3WE9la1BRU3dSaWNKaThR'])
        # self.key_link = '&key=%s' % base64.urlsafe_b64decode(self.key_link)
        self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=id&type=video&maxResults=1&q=%s' + self.key_link
        self.youtube_watch = 'https://www.youtube.com/watch?v=%s'
        self.headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'}

    def play(self, name='', url='', windowedtrailer=0):
        try:
            name = control.infoLabel('ListItem.Title')
            if not name:
                name = control.infoLabel('ListItem.Label')
            if self.content == 'movies':
                name += ' ' + control.infoLabel('ListItem.Year')
            name += ' trailer'
            if control.infoLabel('Container.Content') in ['seasons', 'episodes']:
                season = control.infoLabel('ListItem.Season')
                episode = control.infoLabel('ListItem.Episode')
                if not season is '':
                    name = control.infoLabel('ListItem.TVShowTitle')
                    name += ' season %01d trailer' % int(season)
                    if not episode is '':
                        name = name.replace('season ', '').replace(' trailer', '')
                        name += 'x%02d promo' % int(episode)

            url = self.worker(name, url)
            if not url:return

            icon = control.infoLabel('ListItem.Icon')

            item = control.item(label=name, iconImage=icon, thumbnailImage=icon, path=url)
            item.setInfo(type="video", infoLabels={"title": name})

            item.setProperty('IsPlayable', 'true')
            control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)
            if windowedtrailer == 1:
                # The call to the play() method is non-blocking. So we delay further script execution to keep the script alive at this spot.
                # Otherwise this script will continue and probably already be garbage collected by the time the trailer has ended.
                control.sleep(1000)  # Wait until playback starts. Less than 900ms is too short (on my box). Make it one second.
                while control.player.isPlayingVideo():
                    control.sleep(1000)
                # Close the dialog.
                # Same behaviour as the fullscreenvideo window when :
                # the media plays to the end,
                # or the user pressed one of X, ESC, or Backspace keys on the keyboard/remote to stop playback.
                control.execute("Dialog.Close(%s, true)" % control.getCurrentDialogId)
        except:
            pass

    def playcontext(self, name, url=None, windowedtrailer=0):
        try:
            url = self.worker(name, url)
            if not url: return

            title = control.infoLabel('listitem.title')
            if not title: title = control.infoLabel('listitem.label')
            icon = control.infoLabel('listitem.icon')

            item = control.item(path=url, iconImage=icon, thumbnailImage=icon)
            try: item.setArt({'icon': icon})
            except: pass
            item.setInfo(type='Video', infoLabels={'title': title})
            control.player.play(url, item, windowedtrailer)
            if windowedtrailer == 1:
                # The call to the play() method is non-blocking. So we delay further script execution to keep the script alive at this spot.
                # Otherwise this script will continue and probably already be garbage collected by the time the trailer has ended.
                control.sleep(1000)  # Wait until playback starts. Less than 900ms is too short (on my box). Make it one second.
                while control.player.isPlayingVideo():
                    control.sleep(1000)
                # Close the dialog.
                # Same behaviour as the fullscreenvideo window when :
                # the media plays to the end,
                # or the user pressed one of X, ESC, or Backspace keys on the keyboard/remote to stop playback.
                control.execute("Dialog.Close(%s, true)" % control.getCurrentDialogId)      
        except:
            pass

    def worker(self, name, url):
        try:
            if url.startswith(self.base_link):
                url = self.resolve(url)
                if not url: raise Exception()
                return url
            elif not url.startswith('http'):
                url = self.youtube_watch % url
                url = self.resolve(url)
                if not url: raise Exception()
                return url
            else:
                raise Exception()
        except:
            query = self.search_link % urllib.quote_plus(name)
            return self.search(query)

    def search(self, url):
        try:
            apiLang = control.apiLanguage().get('youtube', 'en')

            if apiLang != 'en':
                url += "&relevanceLanguage=%s" % apiLang

            try:
                result = client.request(url, headers=self.headers)
                return result.status
            except:
                if result == None:
                    import xbmcgui
                    dialog = xbmcgui.Dialog()
                    dialog.notification('Youtube API Quota limit', 'Please use Your Personal Api in Youtube settings.', xbmcgui.NOTIFICATION_INFO, 5000)
                    return

            items = json.loads(result).get('items', [])
            items = [i.get('id', {}).get('videoId') for i in items]

            for vid_id in items:
                url = self.resolve(vid_id)
                if url:
                    return url
        except:
            return

    def resolve(self, url):
        try:
            id = url.split('?v=')[-1].split('/')[-1].split('?')[0].split('&')[0]
            result = client.request(self.youtube_watch % id, headers=self.headers)

            message = client.parseDOM(result, 'div', attrs={'id': 'unavailable-submessage'})
            message = ''.join(message)

            alert = client.parseDOM(result, 'div', attrs={'id': 'watch7-notification-area'})

            if len(alert) > 0: raise Exception()
            if re.search('[a-zA-Z]', message): raise Exception()

            url = 'plugin://plugin.video.myyoutuber/?url=videoid@@@@%s&mode=3' % id
            return url
        except:
            return
