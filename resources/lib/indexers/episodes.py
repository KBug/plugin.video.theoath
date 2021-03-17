# -*- coding: utf-8 -*-

"""
    Exodus Add-on
    ///Updated for TheOath///

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


from resources.lib.modules import trakt
from resources.lib.modules import bookmarks
from resources.lib.modules import cleangenre
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules import cache
from resources.lib.modules import playcount
from resources.lib.modules import workers
from resources.lib.modules import views
from resources.lib.modules import utils
from resources.lib.modules import api_keys
from resources.lib.modules import log_utils

import six
from six.moves import urllib_parse

import os,sys,re,datetime,traceback
import simplejson as json

import requests

params = dict(urllib_parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()

action = params.get('action')

class seasons:
    def __init__(self):
        self.list = []

        self.showunaired = control.setting('showunaired') or 'true'
        self.specials = control.setting('tv.specials') or 'true'
        self.datetime = datetime.datetime.utcnow()# - datetime.timedelta(hours = 5)
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.lang = control.apiLanguage()['tmdb'] or 'en'

        self.tm_user = control.setting('tm.user') or api_keys.tmdb_key
        self.tmdb_show_link = 'https://api.themoviedb.org/3/tv/%s?api_key=%s&language=%s&append_to_response=aggregate_credits,content_ratings' % ('%s', self.tm_user, '%s')
        self.tmdb_show_lite_link = 'https://api.themoviedb.org/3/tv/%s?api_key=%s&language=en' % ('%s', self.tm_user)
        self.tmdb_by_imdb = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', self.tm_user)
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'


    def get(self, tvshowtitle, year, imdb, tmdb, idx=True, create_directory=True):

        if idx == True:
            self.list = cache.get(self.tmdb_list, 24, tvshowtitle, year, imdb, tmdb)
            if create_directory == True: self.seasonDirectory(self.list)
            return self.list
        else:
            self.list = self.tmdb_list(tvshowtitle, year, imdb, tmdb, lite=True)
            return self.list


    def tmdb_list(self, tvshowtitle, year, imdb, tmdb, lite=False):
        try:

            tvdb = '0'

            if tmdb == '0' and not imdb == '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = requests.get(url, timeout=10).json()
                    id = result.get('tv_results', [])[0]
                    tmdb = id.get('id')
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            if imdb == '0' or tmdb == '0':
                try:
                    ids_from_trakt = trakt.SearchTVShow(tvshowtitle, year, full=False)[0]
                    ids_from_trakt = ids_from_trakt.get('show', '0')
                    if imdb == '0':
                        imdb = ids_from_trakt.get('ids', {}).get('imdb')
                        if not imdb: imdb = '0'
                        else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                    if tmdb == '0':
                        tmdb = ids_from_trakt.get('ids', {}).get('tmdb')
                        if not tmdb: tmdb = '0'
                        else: tmdb = str(tmdb)
                    if tvdb == '0':
                        tvdb = ids_from_trakt.get('ids', {}).get('tvdb')
                        if not tvdb: tvdb = '0'
                        else: tvdb = str(tvdb)
                except:
                    pass

        except:
            # failure = traceback.format_exc()
            # log_utils.log('tmdb-list0 Exception: ' + str(failure))
            return

        try:
            if tmdb == '0': raise Exception()

            seasons_url = self.tmdb_show_link % (tmdb, self.lang) + ',translations'
            seasons_en_url = self.tmdb_show_link % (tmdb, 'en')
            seasons_lite_url = self.tmdb_show_lite_link % tmdb
            if self.lang == 'en':
                item = requests.get(seasons_en_url, timeout=10).json()
            elif lite == True:
                item = requests.get(seasons_lite_url, timeout=10).json()
            else:
                item = requests.get(seasons_url, timeout=10).json()
            item = control.six_decode(item)
            #item = requests.get(url, timeout=10).content
            #item = utils.json_loads_as_str(item)
            #log_utils.log('tmdb_item: ' + str(item))
            if item == None: raise Exception()

            seasons = item['seasons']
            if self.specials == 'false':
                seasons = [s for s in seasons if not s['season_number'] == 0]

            try: studio = item['networks'][0]['name']
            except: studio = ''
            if not studio: studio = '0'

            try:
                genres = item['genres']
                genre = [d['name'] for d in genres]
                genre = ' / '.join(genre)
            except:
                genre = ''
            if not genre: genre = '0'

            try:
                duration = item['episode_run_time'][0]
                duration = str(duration)
            except: duration = ''
            if not duration: duration = '0'

            try:
                m = item['content_ratings']['results']
                mpaa = [d['rating'] for d in m if d['iso_3166_1'] == 'US'][0]
            except: mpaa = ''
            if not mpaa: mpaa = '0'

            try: status = item['status']
            except: status = ''
            if not status: status = '0'

            try:
                c = item['aggregate_credits']['cast'][:30]
                castwiththumb = []
                for person in c:
                    _icon = person['profile_path']
                    icon = self.tm_img_link % ('185', _icon) if _icon else ''
                    castwiththumb.append({'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': icon})
            except:
                castwiththumb = ''
            if not castwiththumb: castwiththumb = cast = ''
            else: cast = [(p['name'], p['role']) for p in castwiththumb]

            try: show_plot = item['overview']
            except: show_plot = ''
            if not show_plot: show_plot = '0'
            show_plot = six.ensure_str(show_plot)

            if not self.lang == 'en' and show_plot == '0':
                try:
                    translations = item.get('translations', {})
                    translations = translations.get('translations', [])
                    fallback_item = [x['data'] for x in translations if x.get('iso_639_1') == 'en'][0]
                    show_plot = fallback_item['overview']
                    show_plot = six.ensure_str(show_plot)
                except:
                    pass

            unaired = ''

            try: poster_path = item['poster_path']
            except: poster_path = ''
            if poster_path: show_poster = self.tm_img_link % ('500', poster_path)
            else: show_poster = '0'

            try: fanart_path = item['backdrop_path']
            except: fanart_path = ''
            if fanart_path: fanart = self.tm_img_link % ('1280', fanart_path)
            else: fanart = '0'

        except:
            # failure = traceback.format_exc()
            # log_utils.log('tmdb-list1 Exception: ' + str(failure))
            pass

        for item in seasons:
            try:
                season = str(int(item['season_number']))

                premiered = item.get('air_date', '0')
                if status == 'Ended': pass
                elif not premiered or premiered == '0': raise Exception()
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true': raise Exception()

                plot = item['overview']
                if plot: plot = client.replaceHTMLCodes(six.ensure_str(plot))
                else: plot = show_plot

                try: poster_path = item['poster_path']
                except: poster_path = ''
                if poster_path: poster = self.tm_img_link % ('500', poster_path)
                else: poster = show_poster

                banner = '0'
                thumb = '0'

                self.list.append({'season': season, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': status, 'studio': studio, 'genre': genre, 'duration': duration, 'mpaa': mpaa,
                                  'cast': cast, 'castwiththumb': castwiththumb, 'plot': plot, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'banner': banner, 'fanart': fanart, 'thumb': thumb, 'unaired': unaired})
                #self.list = sorted(self.list, key=lambda k: int(k['season']))
            except:
                # failure = traceback.format_exc()
                # log_utils.log('seasons_dir Exception: ' + str(failure))
                pass

        return self.list


    def seasonDirectory(self, items):
        if items == None or len(items) == 0: control.idle() ; sys.exit()

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()

        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')

        traktCredentials = trakt.getTraktCredentialsInfo()

        try: isOld = False ; control.item().getArt('type')
        except: isOld = True

        try: indicators = playcount.getSeasonIndicators(items[0]['imdb'])
        except: pass

        watchedMenu = control.lang(32068) if trakt.getTraktIndicatorsInfo() == True else control.lang(32066)

        unwatchedMenu = control.lang(32069) if trakt.getTraktIndicatorsInfo() == True else control.lang(32067)

        queueMenu = control.lang(32065)

        traktManagerMenu = control.lang(32070)

        labelMenu = control.lang(32055)

        playRandom = control.lang(32535)

        addToLibrary = control.lang(32551)

        infoMenu = control.lang(32101)


        for i in items:
            try:
                label = '%s %s' % (labelMenu, i['season'])
                try:
                    if i['unaired'] == 'true':
                        label = '[COLOR crimson][I]%s[/I][/COLOR]' % label
                except:
                    pass
                systitle = sysname = urllib_parse.quote_plus(i['tvshowtitle'])

                imdb, tvdb, tmdb, year, season, fanart, duration, status = i['imdb'], i['tvdb'], i['tmdb'], i['year'], i['season'], i['fanart'], i['duration'], i['status']

                meta = dict((k,v) for k, v in six.iteritems(i) if not (v == '0' or 'cast' in k))
                meta.update({'code': imdb, 'imdbnumber': imdb, 'imdb_id': imdb})
                meta.update({'tvdb_id': tvdb})
                meta.update({'mediatype': 'tvshow'})
                meta.update({'trailer': '%s?action=trailer&name=%s' % (sysaddon, sysname)})
                if not 'duration' in i: meta.update({'duration': '60'})
                elif i['duration'] == '0': meta.update({'duration': '60'})
                try: meta.update({'duration': str(int(meta['duration']) * 60)})
                except: pass
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                except: pass
                try:
                    seasonYear = i['premiered']
                    seasonYear = re.findall('(\d{4})', seasonYear)[0]
                    seasonYear = six.ensure_str(seasonYear)
                    meta.update({'year': seasonYear})
                except:
                    pass

                try:
                    overlay = int(playcount.getSeasonOverlay(indicators, imdb, season))
                    if overlay == 7: meta.update({'playcount': 1, 'overlay': 7})
                    else: meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass

                cm = []

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=episode&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&season=%s)' % (sysaddon, urllib_parse.quote_plus(systitle), urllib_parse.quote_plus(year), urllib_parse.quote_plus(imdb), urllib_parse.quote_plus(tmdb), urllib_parse.quote_plus(season))))

                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                cm.append((watchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tmdb=%s&season=%s&query=7)' % (sysaddon, systitle, imdb, tmdb, season)))

                cm.append((unwatchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tmdb=%s&season=%s&query=6)' % (sysaddon, systitle, imdb, tmdb, season)))

                if traktCredentials == True:
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, sysname, tmdb)))

                if isOld == True:
                    cm.append((infoMenu, 'Action(Info)'))

                cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, systitle, year, imdb, tmdb)))

                try: item = control.item(label=label, offscreen=True)
                except: item = control.item(label=label)


                art = {}

                if 'thumb' in i and not i['thumb'] == '0':
                    art.update({'icon': i['thumb'], 'thumb': i['thumb'], 'poster': i['thumb']})
                elif 'poster' in i and not i['poster'] == '0':
                    art.update({'icon': i['poster'], 'thumb': i['poster'], 'poster': i['poster']})
                else:
                    art.update({'icon': addonPoster, 'thumb': addonPoster, 'poster': addonPoster})

                if 'banner' in i and not i['banner'] == '0':
                    art.update({'banner': i['banner']})
                elif 'fanart' in i and not i['fanart'] == '0':
                    art.update({'banner': i['fanart']})
                else:
                    art.update({'banner': addonBanner})

                if settingFanart == 'true' and 'fanart' in i and not i['fanart'] == '0':
                    art.update({'fanart': i['fanart']})
                elif not addonFanart == None:
                    art.update({'fanart': addonFanart})

                castwiththumb = i.get('castwiththumb', []) or []
                cast = i.get('cast', []) or []
                try: item.setCast(castwiththumb)
                except: meta.update({'cast': cast})
                item.setArt(art)
                item.addContextMenuItems(cm)
                item.setInfo(type='Video', infoLabels = control.metadataClean(meta))

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&fanart=%s&duration=%s&status=%s&season=%s' % (sysaddon, systitle, year, imdb, tmdb, fanart, duration, status, season)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                # failure = traceback.format_exc()
                # log_utils.log('season-dir Exception: ' + str(failure))
                pass

        try: control.property(syshandle, 'showplot', items[0]['plot'])
        except: pass

        control.content(syshandle, 'seasons')
        control.directory(syshandle, cacheToDisc=True)
        views.setView('seasons', {'skin.estuary': 55, 'skin.confluence': 500})


class episodes:
    def __init__(self):
        self.list = []

        self.trakt_link = 'https://api.trakt.tv'
        self.tvmaze_link = 'https://api.tvmaze.com'
        self.datetime = datetime.datetime.utcnow()# - datetime.timedelta(hours = 5)
        self.systime = self.datetime.strftime('%Y%m%d%H%M%S%f')
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.trakt_user = control.setting('trakt.user').strip()
        self.showunaired = control.setting('showunaired') or 'true'
        self.specials = control.setting('tv.specials') or 'true'
        self.lang = control.apiLanguage()['tmdb'] or 'en'

        self.tm_user = control.setting('tm.user') or api_keys.tmdb_key
        self.tmdb_season_link = 'https://api.themoviedb.org/3/tv/%s/season/%s?api_key=%s&language=%s&append_to_response=aggregate_credits' % ('%s', '%s', self.tm_user, '%s')
        self.tmdb_season_lite_link = 'https://api.themoviedb.org/3/tv/%s/season/%s?api_key=%s&language=en' % ('%s', '%s', self.tm_user)
        self.tmdb_episode_link = 'https://api.themoviedb.org/3/tv/%s/season/%s/episode/%s?api_key=%s&language=%s&append_to_response=credits' % ('%s', '%s', '%s', self.tm_user, self.lang)
        self.tmdb_by_imdb = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', self.tm_user)
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'

        self.added_link = 'https://api.tvmaze.com/schedule'
        #https://api.trakt.tv/calendars/all/shows/date[30]/31 #use this for new episodes?
        #self.mycalendar_link = 'https://api.trakt.tv/calendars/my/shows/date[29]/60/'
        self.mycalendar_link = 'https://api.trakt.tv/calendars/my/shows/date[30]/31/' #go back 30 and show all shows aired until tomorrow
        self.trakthistory_link = 'https://api.trakt.tv/users/me/history/shows?limit=40'
        self.progress_link = 'https://api.trakt.tv/users/me/watched/shows'
        self.hiddenprogress_link = 'https://api.trakt.tv/users/hidden/progress_watched?limit=1000&type=show'
        self.calendar_link = 'https://api.tvmaze.com/schedule?date=%s'
        self.onDeck_link = 'https://api.trakt.tv/sync/playback/episodes?limit=20'
        self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
        self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000'
        self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items'


    def get(self, tvshowtitle, year, imdb, tmdb, fanart=None, duration=None, status=None, season=None, episode=None, idx=True, create_directory=True):
        try:
            if idx == True:
                if season == None or episode == None:
                    self.list = cache.get(self.tmdb_list, 1, tvshowtitle, year, imdb, tmdb, fanart, duration, status, season)
                # elif episode == None:
                    # self.list = cache.get(self.tmdb_list, 1, tvshowtitle, year, imdb, tmdb, fanart, duration, status, season)
                else:
                    self.list = cache.get(self.tmdb_list, 1, tvshowtitle, year, imdb, tmdb, fanart, duration, status, season)
                    num = [x for x,y in enumerate(self.list) if y['season'] == str(season) and y['episode'] == str(episode)][-1]
                    self.list = [y for x,y in enumerate(self.list) if x >= num]

                if create_directory == True: self.episodeDirectory(self.list)
                return self.list

            else:
                self.list = self.tmdb_list(tvshowtitle, year, imdb, tmdb, fanart=None, duration=None, status=None, season=season, lite=True)
                return self.list
        except:
            # failure = traceback.format_exc()
            # log_utils.log('episodes_get Exception: ' + str(failure))
            pass


    def calendar(self, url):
        try:

            try: url = getattr(self, url + '_link')
            except: pass

            if self.trakt_link in url and url == self.onDeck_link:
                self.blist = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                self.list = []
                self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: int(k['paused_at']), reverse=True)

            elif self.trakt_link in url and url == self.progress_link:
                self.blist = cache.get(self.trakt_progress_list, 720, url, self.trakt_user, self.lang)
                self.list = []
                self.list = cache.get(self.trakt_progress_list, 0, url, self.trakt_user, self.lang)

            elif self.trakt_link in url and url == self.mycalendar_link:
                self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                self.list = []
                self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)

            elif self.trakt_link in url and '/users/' in url:
                self.list = cache.get(self.trakt_list, 0.3, url, self.trakt_user)
                self.list = self.list[::-1]

            elif self.trakt_link in url:
                self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)


            elif self.tvmaze_link in url and url == self.added_link:
                urls = [i['url'] for i in self.calendars(idx=False)][:5]
                self.list = []
                for url in urls:
                    self.list += cache.get(self.tvmaze_list, 720, url, True)

            elif self.tvmaze_link in url:
                self.list = cache.get(self.tvmaze_list, 1, url, False)


            self.episodeDirectory(self.list)
            return self.list
        except:
            pass


    def widget(self):
        if trakt.getTraktIndicatorsInfo() == True:
            setting = control.setting('tv.widget.alt')
        else:
            setting = control.setting('tv.widget')

        if setting == '2':
            self.calendar(self.progress_link)
        elif setting == '3':
            self.calendar(self.mycalendar_link)
        else:
            self.calendar(self.added_link)


    def calendars(self, idx=True):
        m = control.lang(32060).split('|')
        try: months = [(m[0], 'January'), (m[1], 'February'), (m[2], 'March'), (m[3], 'April'), (m[4], 'May'), (m[5], 'June'), (m[6], 'July'), (m[7], 'August'), (m[8], 'September'), (m[9], 'October'), (m[10], 'November'), (m[11], 'December')]
        except: months = []

        d = control.lang(32061).split('|')
        try: days = [(d[0], 'Monday'), (d[1], 'Tuesday'), (d[2], 'Wednesday'), (d[3], 'Thursday'), (d[4], 'Friday'), (d[5], 'Saturday'), (d[6], 'Sunday')]
        except: days = []

        for i in list(range(0, 30)):
            try:
                name = (self.datetime - datetime.timedelta(days = i))
                name = (control.lang(32062) % (name.strftime('%A'), six.ensure_str(name.strftime('%d %B'))))
                for m in months: name = name.replace(m[1], m[0])
                for d in days: name = name.replace(d[1], d[0])
                try: name = six.ensure_str(name)
                except: pass

                url = self.calendar_link % (self.datetime - datetime.timedelta(days = i)).strftime('%Y-%m-%d')

                self.list.append({'name': name, 'url': url, 'image': 'calendar.png', 'action': 'calendar'})
            except:
                pass
        if idx == True: self.addDirectory(self.list)
        return self.list


    def userlists(self):
        try:
            userlists = []
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            activity = trakt.getActivity()
        except:
            pass

        try:
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlists_link, self.trakt_user): raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link, self.trakt_user)
        except:
            pass
        try:
            self.list = []
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link, self.trakt_user): raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlikedlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user)
        except:
            pass

        self.list = userlists
        for i in list(range(0, len(self.list))): self.list[i].update({'image': 'userlists.png', 'action': 'calendar'})
        self.addDirectory(self.list, queue=True)
        return self.list


    def trakt_list(self, url, user):
        try:
            for i in re.findall('date\[(\d+)\]', url):
                url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days = int(i))).strftime('%Y-%m-%d'))

            q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib_parse.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q

            itemlist = []
            items = trakt.getTraktAsJson(u)
        except:
            print("Unexpected error in info builder script:", sys.exc_info()[0])
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(exc_type, exc_tb.tb_lineno)
            return


        for item in items:
            try:
                title = item['episode']['title']
                if title == None or title == '': raise Exception()
                title = client.replaceHTMLCodes(title)

                season = item['episode']['season']
                season = re.sub('[^0-9]', '', '%01d' % int(season))
                if season == '0': raise Exception()

                episode = item['episode']['number']
                episode = re.sub('[^0-9]', '', '%01d' % int(episode))
                if episode == '0': raise Exception()

                tvshowtitle = item['show']['title']
                if tvshowtitle == None or tvshowtitle == '': raise Exception()
                tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                year = item['show']['year']
                year = re.sub('[^0-9]', '', str(year))

                imdb = item['show']['ids']['imdb']
                if imdb == None or imdb == '': imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tvdb = item['show']['ids']['tvdb']
                if not tvdb: tvdb == '0'
                tvdb = re.sub('[^0-9]', '', str(tvdb))

                tmdb = item['show']['ids']['tmdb']
                if not tmdb: raise Exception()
                tmdb = str(tmdb)

                premiered = item['episode']['first_aired']
                try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                except: premiered = '0'

                studio = item['show']['network']
                if studio == None: studio = '0'

                genre = item['show']['genres']
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)

                try: duration = str(item['show']['runtime'])
                except: duration = '0'
                if duration == None: duration = '0'

                try: rating = str(item['episode']['rating'])
                except: rating = '0'
                if rating == None or rating == '0.0': rating = '0'

                try: votes = str(item['episode']['votes'])
                except: votes = '0'
                try: votes = str(format(int(votes),',d'))
                except: pass
                if votes == None: votes = '0'

                mpaa = item['show']['certification']
                if mpaa == None: mpaa = '0'

                plot = item['episode']['overview']
                if plot == None or plot == '': plot = item['show']['overview']
                if plot == None or plot == '': plot = '0'
                plot = client.replaceHTMLCodes(plot)

                try:
                    if self.lang == 'en': raise Exception()

                    item = trakt.getTVShowTranslation(imdb, lang=self.lang, season=season, episode=episode, full=True)

                    title = item.get('title') or title
                    plot = item.get('overview') or plot

                    tvshowtitle = trakt.getTVShowTranslation(imdb, lang=self.lang) or tvshowtitle
                except:
                    pass

                paused_at = item.get('paused_at', '0') or '0'
                paused_at = re.sub('[^0-9]+', '', paused_at)

                itemlist.append({'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': 'Continuing', 'studio': studio, 'genre': genre,
                                 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'poster': '0', 'thumb': '0', 'paused_at': paused_at})
            except:
                pass

        itemlist = itemlist[::-1]
        return itemlist


    def trakt_progress_list(self, url, user, lang):
        try:
            url += '?extended=full'
            result = trakt.getTraktAsJson(url)
            #log_utils.log('prog_res: ' + str(result))
            items = []
        except:
            return

        sortorder = control.setting('prgr.sortorder')
        for item in result:
            try:
                num_1 = 0
                for i in range(0, len(item['seasons'])):
                    if item['seasons'][i]['number'] > 0: num_1 += len(item['seasons'][i]['episodes'])
                num_2 = int(item['show']['aired_episodes'])
                if num_1 >= num_2: raise Exception()

                season = str(item['seasons'][-1]['number'])

                episode = [x for x in item['seasons'][-1]['episodes'] if 'number' in x]
                episode = sorted(episode, key=lambda x: x['number'])
                episode = str(episode[-1]['number'])

                tvshowtitle = item['show']['title']
                if tvshowtitle == None or tvshowtitle == '': raise Exception()
                tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                year = item['show']['year']
                year = re.sub('[^0-9]', '', str(year))
                if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = item['show']['ids']['imdb']
                if imdb == None or imdb == '': imdb = '0'

                tvdb = item['show']['ids']['tvdb']
                #if tvdb == None or tvdb == '': raise Exception()
                tvdb = re.sub('[^0-9]', '', str(tvdb))

                tmdb = item['show']['ids']['tmdb']
                if not tmdb: tmdb = '0'
                else: tmdb = str(tmdb)

                studio = item.get('show').get('network', '0')
                if studio == None or studio == '': studio = '0'

                duration = item['show']['runtime']
                if not duration: duration = '0'

                mpaa = item['show']['certification']
                if not mpaa: mpaa = '0'

                status = item['show']['status']
                if not status: status = '0'

                genre = item['show']['genres']
                if genre == []: genre = '0'
                genre = ' / '.join(genre)

                last_watched = item['last_watched_at']
                if last_watched == None or last_watched == '': last_watched = '0'
                items.append({'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'tvshowtitle': tvshowtitle, 'year': year, 'studio': studio, 'duration': duration, 'mpaa': mpaa, 'status': status,
                              'genre': genre, 'snum': season, 'enum': episode, '_last_watched': last_watched})
            except:
                pass

        try:
            result = trakt.getTraktAsJson(self.hiddenprogress_link)
            #log_utils.log('hid_prog_res: ' + str(result))
            result = [str(i['show']['ids']['tmdb']) for i in result]

            items = [i for i in items if not i['tmdb'] in result]
        except:
            # failure = traceback.format_exc()
            # log_utils.log('TProgress1: ' + str(failure))
            pass

        def items_list(i):

            tmdb = i['tmdb']
            if (not tmdb or tmdb == '0') and not i['imdb'] == '0':
                try:
                    url = self.tmdb_by_imdb % i['imdb']
                    result = requests.get(url, timeout=10).json()
                    id = result.get('tv_results', [])[0]
                    tmdb = id.get('id')
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            try:
                item = [x for x in self.blist if x['tmdb'] == tmdb and x['snum'] == i['snum'] and x['enum'] == i['enum']][0]
                item['action'] = 'episodes'
                self.list.append(item)
                return
            except:
                pass

            try:
                if tmdb == '0': raise Exception()

                _episode = str(int(i['enum']) + 1)
                _season = str(int(i['snum']) + 1)

                url = self.tmdb_episode_link % (tmdb, i['snum'], _episode)
                result = requests.get(url, timeout=10).json()
                if result.get('success') == False:
                    url2 = self.tmdb_episode_link % (tmdb, _season, '1')
                    result = requests.get(url2, timeout=10).json()
                item = control.six_decode(result)

                try: premiered = item['air_date']
                except: premiered = ''
                if not premiered: premiered = '0'
                premiered = six.ensure_str(premiered)

                unaired = ''
                if i['status'] == 'Ended': pass
                elif premiered == '0': raise Exception()
                elif int(re.sub(r'[^0-9]', '', str(premiered))) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true': raise Exception()

                title = item['name']
                if title == '': title = '0'
                title = client.replaceHTMLCodes(title)
                title = six.ensure_str(title)

                season = item['season_number']
                season = '%01d' % season
                #if int(season) == 0:# and self.specials != 'true':
                    #raise Exception()

                episode = item['episode_number']
                episode = '%01d' % episode

                tvshowtitle = i['tvshowtitle']
                imdb, tvdb = i['imdb'], i['tvdb']

                year = i['year']
                try: year = six.ensure_str(year)
                except: pass

                poster = '0'

                banner = '0'

                fanart = '0'

                try: thumb = self.tm_img_link % ('300', item['still_path'])
                except: thumb = ''
                if not thumb : thumb = '0'

                try: rating = str(item['vote_average'])
                except: rating = ''
                if not rating: rating = '0'

                try: votes = str(item['vote_count'])
                except: votes = ''
                if not votes: votes = '0'

                try:
                    plot = item['overview']
                    plot = six.ensure_str(plot)
                except:
                    plot = ''
                if not plot: plot = '0'

                try:
                    r_crew = item['crew']
                    director = [d for d in r_crew if d['job'] == 'Director']
                    director = ', '.join([d['name'] for d in director])
                    writer = [w for w in r_crew if w['job'] == 'Writer']
                    writer = ', '.join([w['name'] for w in writer])
                except:
                    director = writer = ''
                if not director: director = '0'
                if not writer: writer = '0'

                try:
                    r_cast = item['credits']['cast'][:30]
                    castwiththumb = []
                    for person in r_cast:
                        _icon = person['profile_path']
                        icon = self.tm_img_link % ('185', _icon) if _icon else ''
                        castwiththumb.append({'name': person['name'], 'role': person['character'], 'thumbnail': icon})
                except:
                    castwiththumb = ''
                if not castwiththumb: castwiththumb = cast = ''
                else: cast = [(p['name'], p['role']) for p in castwiththumb]

                self.list.append({'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'studio': i.get('studio'), 'genre': i.get('genre'), 'status': i.get('status'),
                                  'duration': i.get('duration'), 'rating': rating, 'votes': votes, 'mpaa': i.get('mpaa'), 'director': director, 'writer': writer, 'cast': cast, 'castwiththumb': castwiththumb, 'plot': plot,
                                  'poster': poster, 'banner': banner, 'fanart': fanart, 'thumb': thumb, 'snum': i['snum'], 'enum': i['enum'], 'action': 'episodes', 'unaired': unaired, '_last_watched': i['_last_watched'],
                                  'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, '_sort_key': max(i['_last_watched'],premiered)})
            except:
                # failure = traceback.format_exc()
                # log_utils.log('TProgress: ' + str(failure))
                pass


        items = items[:50]

        threads = []
        for i in items: threads.append(workers.Thread(items_list, i))
        [i.start() for i in threads]
        [i.join() for i in threads]


        try:
            if sortorder == '0':
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
            else:
                self.list = sorted(self.list, key=lambda k: k['_sort_key'], reverse=True)
        except: pass

        return self.list


    def trakt_episodes_list(self, url, user, lang):
        items = self.trakt_list(url, user)

        def items_list(i):

            tmdb = i['tmdb']
            if (not tmdb or tmdb == '0') and not i['imdb'] == '0':
                try:
                    url = self.tmdb_by_imdb % i['imdb']
                    result = requests.get(url, timeout=10).json()
                    id = result.get('tv_results', [])[0]
                    tmdb = id.get('id')
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            try:
                item = [x for x in self.blist if x['tmdb'] == tmdb and x['season'] == i['season'] and x['episode'] == i['episode']][0]
                if item['poster'] == '0': raise Exception()
                self.list.append(item)
                return
            except:
                pass

            try:
                if tmdb == '0': raise Exception()

                if i['season'] == '0': raise Exception()
                url = self.tmdb_episode_link % (tmdb, i['season'], i['episode'])
                result = requests.get(url, timeout=10).json()
                item = control.six_decode(result)

                try: premiered = item['air_date']
                except: premiered = ''
                if not premiered: premiered = '0'
                premiered = six.ensure_str(premiered)

                title = item['name']
                if title == '': title = '0'
                title = client.replaceHTMLCodes(title)
                title = six.ensure_str(title)

                season = item['season_number']
                season = '%01d' % season
                #if int(season) == 0:# and self.specials != 'true':
                    #raise Exception()

                episode = item['episode_number']
                episode = '%01d' % episode

                tvshowtitle = i['tvshowtitle']
                imdb, tvdb = i['imdb'], i['tvdb']

                status, duration, mpaa, studio, genre = i['status'], i['duration'], i['mpaa'], i['studio'], i['genre']

                year = i['year']
                try: year = six.ensure_str(year)
                except: pass

                poster = '0'

                banner = '0'

                fanart = '0'

                try: thumb = self.tm_img_link % ('300', item['still_path'])
                except: thumb = ''
                if not thumb : thumb = '0'

                rating, votes = i['rating'], i['votes']

                try:
                    plot = item['overview']
                    plot = six.ensure_str(plot)
                except:
                    plot = ''
                if not plot: plot = i['plot']

                try:
                    r_crew = item['crew']
                    director = [d for d in r_crew if d['job'] == 'Director']
                    director = ', '.join([d['name'] for d in director])
                    writer = [w for w in r_crew if w['job'] == 'Writer']
                    writer = ', '.join([w['name'] for w in writer])
                except:
                    director = writer = ''
                if not director: director = '0'
                if not writer: writer = '0'

                try:
                    r_cast = item['credits']['cast'][:30]
                    castwiththumb = []
                    for person in r_cast:
                        _icon = person['profile_path']
                        icon = self.tm_img_link % ('185', _icon) if _icon else ''
                        castwiththumb.append({'name': person['name'], 'role': person['character'], 'thumbnail': icon})
                except:
                    castwiththumb = ''
                if not castwiththumb: castwiththumb = cast = ''
                else: cast = [(p['name'], p['role']) for p in castwiththumb]

                paused_at = i.get('paused_at', '0') or '0'
                paused_at = re.sub('[^0-9]+', '', paused_at)

                #log_utils.log('ondeck_pause: ' + str(paused_at) + ' - ' + str(tvshowtitle))

                self.list.append({'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': status, 'studio': studio, 'genre': genre,
                                  'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': writer, 'castwiththumb': castwiththumb, 'cast': cast, 'plot': plot,
                                  'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'poster': poster, 'banner': banner, 'fanart': fanart, 'thumb': thumb, 'paused_at': paused_at})
            except:
                pass


        items = items[:100]

        threads = []
        for i in items: threads.append(workers.Thread(items_list, i))
        [i.start() for i in threads]
        [i.join() for i in threads]

        return self.list


    def trakt_user_list(self, url, user):
        try:
            items = trakt.getTraktAsJson(url)
        except:
            pass

        for item in items:
            try:
                try: name = item['list']['name']
                except: name = item['name']
                name = client.replaceHTMLCodes(name)

                try: url = (trakt.slug(item['list']['user']['username']), item['list']['ids']['slug'])
                except: url = ('me', item['ids']['slug'])
                url = self.traktlist_link % url
                url = six.ensure_str(url)

                self.list.append({'name': name, 'url': url, 'context': url})
            except:
                pass

        self.list = sorted(self.list, key=lambda k: utils.title_key(k['name']))
        return self.list


    def tvmaze_list(self, url, limit):
        try:
            result = client.request(url)

            itemlist = []
            items = json.loads(result)
        except:
            return

        for item in items:
            try:
                if not 'english' in item['show']['language'].lower(): raise Exception()

                if limit == True and not 'scripted' in item['show']['type'].lower(): raise Exception()

                title = item['name']
                if title == None or title == '': raise Exception()
                title = client.replaceHTMLCodes(title)
                title = six.ensure_str(title)

                season = item['season']
                season = re.sub('[^0-9]', '', '%01d' % int(season))
                if season == '0': raise Exception()
                season = six.ensure_str(season)

                episode = item['number']
                episode = re.sub('[^0-9]', '', '%01d' % int(episode))
                if episode == '0': raise Exception()
                episode = six.ensure_str(episode)

                tvshowtitle = item['show']['name']
                if tvshowtitle == None or tvshowtitle == '': raise Exception()
                tvshowtitle = client.replaceHTMLCodes(tvshowtitle)
                tvshowtitle = six.ensure_str(tvshowtitle)

                year = item['show']['premiered']
                year = re.findall('(\d{4})', year)[0]
                year = six.ensure_str(year)

                imdb = item['show']['externals']['imdb']
                if imdb == None or imdb == '': imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                imdb = six.ensure_str(imdb)

                tvdb = item['show']['externals']['thetvdb']
                if tvdb == None or tvdb == '': tvdb = '0' #raise Exception()
                tvdb = re.sub('[^0-9]', '', str(tvdb))
                tvdb = six.ensure_str(tvdb)

                poster = '0'
                try: poster = item['show']['image']['original']
                except: poster = '0'
                if poster == None or poster == '': poster = '0'
                poster = six.ensure_str(poster)

                try: thumb1 = item['show']['image']['original']
                except: thumb1 = '0'
                try: thumb2 = item['image']['original']
                except: thumb2 = '0'
                if thumb2 == None or thumb2 == '0': thumb = thumb1
                else: thumb = thumb2
                if thumb == None or thumb == '': thumb = '0'
                thumb = six.ensure_str(thumb)

                premiered = item['airdate']
                try: premiered = re.findall('(\d{4}-\d{2}-\d{2})', premiered)[0]
                except: premiered = '0'
                premiered = six.ensure_str(premiered)

                try: studio = item['show']['network']['name']
                except: studio = '0'
                if studio == None: studio = '0'
                studio = six.ensure_str(studio)

                try: genre = item['show']['genres']
                except: genre = '0'
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)
                genre = six.ensure_str(genre)

                try: duration = item['show']['runtime']
                except: duration = '0'
                if duration == None: duration = '0'
                duration = str(duration)
                duration = six.ensure_str(duration)

                try: rating = item['show']['rating']['average']
                except: rating = '0'
                if rating == None or rating == '0.0': rating = '0'
                rating = str(rating)
                rating = six.ensure_str(rating)

                votes = '0'

                try: plot = item['show']['summary']
                except: plot = '0'
                if plot == None: plot = '0'
                plot = re.sub('<.+?>|</.+?>|\n', '', plot)
                plot = client.replaceHTMLCodes(plot)
                plot = six.ensure_str(plot)

                itemlist.append({'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': 'Continuing', 'studio': studio,
                                 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'plot': plot, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0', 'poster': poster, 'thumb': thumb})
            except:
                pass

        itemlist = itemlist[::-1]

        return itemlist


    def tmdb_list(self, tvshowtitle, year, imdb, tmdb, fanart, duration, status, season, lite=False):
        try:

            tvdb = '0'

            if tmdb == '0' and not imdb == '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = requests.get(url, timeout=10).json()
                    id = result.get('tv_results', [])[0]
                    tmdb = id.get('id')
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            if imdb == '0' or tmdb == '0':
                try:
                    ids_from_trakt = trakt.SearchTVShow(tvshowtitle, year, full=False)[0]
                    ids_from_trakt = ids_from_trakt.get('show', '0')
                    if imdb == '0':
                        imdb = ids_from_trakt.get('ids', {}).get('imdb')
                        if not imdb: imdb = '0'
                        else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                    if tmdb == '0':
                        tmdb = ids_from_trakt.get('ids', {}).get('tmdb')
                        if not tmdb: tmdb = '0'
                        else: tmdb = str(tmdb)
                    if tvdb == '0':
                        tvdb = ids_from_trakt.get('ids', {}).get('tvdb')
                        if not tvdb: tvdb = '0'
                        else: tvdb = str(tvdb)
                except:
                    pass

        except:
            # failure = traceback.format_exc()
            # log_utils.log('tmdb_list0 Exception: ' + str(failure))
            return

        try:
            if tmdb == '0': raise Exception()

            episodes_url = self.tmdb_season_link % (tmdb, season, self.lang)
            episodes_en_url = self.tmdb_season_lite_link % (tmdb, season)
            episodes_lite_url = self.tmdb_season_lite_link % (tmdb, season)
            if lite == False:
                result = requests.get(episodes_url, timeout=10).json()
            else:
                result = requests.get(episodes_lite_url, timeout=10).json()
            result = control.six_decode(result)
            episodes = result.get('episodes', [])
            r_cast = result.get('aggregate_credits', {}).get('cast', [])
            if self.specials == 'false':
                episodes = [e for e in episodes if not e['season_number'] == 0]
        except:
            # failure = traceback.format_exc()
            # log_utils.log('tmdb_list1 Exception: ' + str(failure))
            return

        try: poster = self.tm_img_link % ('500', result['poster_path'])
        except: poster = ''
        if not poster: poster = '0'

        if not fanart: fanart = '0'

        for item in episodes:
            try:
                title = item['name']
                if title == '': title = '0'
                title = six.ensure_str(title)

                label = title

                season = str(item['season_number'])

                episode = str(item['episode_number'])

                try: premiered = item['air_date']
                except: premiered = '0'

                unaired = ''
                if not premiered or premiered == '0': pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true': raise Exception()

                try: rating = str(item['vote_average'])
                except: rating = ''
                if not rating: rating = '0'

                try: votes = str(item['vote_count'])
                except: votes = ''
                if not votes: votes = '0'

                try:
                    episodeplot = item['overview']
                except:
                    episodeplot = ''
                if not episodeplot: episodeplot = '0'
                else: episodeplot = client.replaceHTMLCodes(six.ensure_str(episodeplot))

                # if not self.lang == 'en' and episodeplot == '0':
                    # try:
                        # en_item = en_result.get('episodes', [])
                        # episodeplot = en_item['overview']
                        # episodeplot = six.ensure_str(episodeplot)
                    # except:
                        # episodeplot = ''
                    # if not episodeplot: episodeplot = '0'

                try:
                    r_crew = item['crew']
                    director = [d for d in r_crew if d['job'] == 'Director']
                    director = ', '.join([d['name'] for d in director])
                    writer = [w for w in r_crew if w['job'] == 'Writer']
                    writer = ', '.join([w['name'] for w in writer])
                except:
                    director = writer = ''
                if not director: director = '0'
                if not writer: writer = '0'

                try:
                    castwiththumb = []
                    for person in r_cast[:30]:
                        _icon = person['profile_path']
                        icon = self.tm_img_link % ('185', _icon) if _icon else ''
                        castwiththumb.append({'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': icon})
                except:
                    castwiththumb = ''
                if not castwiththumb: castwiththumb = cast = ''
                else: cast = [(p['name'], p['role']) for p in castwiththumb]

                thumb = self.tm_img_link % ('300', item['still_path'])
                banner = '0'

                self.list.append({'title': title, 'label': label, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered,
                                  'rating': rating, 'votes': votes, 'director': director, 'writer': writer, 'cast': cast, 'castwiththumb': castwiththumb, 'duration': duration, 'status': status,
                                  'plot': episodeplot, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'banner': banner, 'fanart': fanart, 'thumb': thumb, 'unaired': unaired})
                #self.list = sorted(self.list, key=lambda k: (int(k['season']), int(k['episode'])))
            except:
                # failure = traceback.format_exc()
                # log_utils.log('tmdb_list2 Exception: ' + str(failure))
                pass

        return self.list


    def episodeDirectory(self, items):
        if items == None or len(items) == 0: control.idle() ; sys.exit()

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()

        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')

        traktCredentials = trakt.getTraktCredentialsInfo()

        try: isOld = False ; control.item().getArt('type')
        except: isOld = True

        isPlayable = 'true' if not 'plugin' in control.infoLabel('Container.PluginName') else 'false'

        indicators = playcount.getTVShowIndicators(refresh=True)

        try: multi = [i['tvshowtitle'] for i in items]
        except: multi = []
        multi = len([x for y,x in enumerate(multi) if x not in multi[:y]])
        multi = True if multi > 1 else False

        try: sysaction = items[0]['action']
        except: sysaction = ''

        isFolder = False if not sysaction == 'episodes' else True

        playbackMenu = control.lang(32063) if control.setting('hosts.mode') == '2' else control.lang(32064)

        watchedMenu = control.lang(32068) if trakt.getTraktIndicatorsInfo() == True else control.lang(32066)

        unwatchedMenu = control.lang(32069) if trakt.getTraktIndicatorsInfo() == True else control.lang(32067)

        queueMenu = control.lang(32065)

        traktManagerMenu = control.lang(32070)

        tvshowBrowserMenu = control.lang(32071)

        addToLibrary = control.lang(32551)

        infoMenu = control.lang(32101)

        clearProviders = control.lang(32081)

        for i in items:
            try:
                if not 'label' in i: i['label'] = i['title']

                if i['label'] == '0':
                    label = '%sx%02d . %s %s' % (i['season'], int(i['episode']), 'Episode', i['episode'])
                else:
                    label = '%sx%02d . %s' % (i['season'], int(i['episode']), i['label'])
                if multi == True:
                    label = '%s - %s' % (i['tvshowtitle'], label)

                try:
                    if i['unaired'] == 'true':
                        label = '[COLOR crimson][I]%s[/I][/COLOR]' % label
                except:
                    pass

                imdb, tvdb, tmdb, year, season, episode = i['imdb'], i['tvdb'], i['tmdb'], i['year'], i['season'], i['episode']

                systitle = urllib_parse.quote_plus(i['title'])
                systvshowtitle = urllib_parse.quote_plus(i['tvshowtitle'])
                syspremiered = urllib_parse.quote_plus(i['premiered'])

                meta = dict((k,v) for k, v in six.iteritems(i) if not (v == '0' or 'cast' in k))
                meta.update({'mediatype': 'episode'})
                meta.update({'code': imdb, 'imdbnumber': imdb})
                meta.update({'trailer': '%s?action=trailer&name=%s' % (sysaddon, systvshowtitle)})
                if not 'duration' in i: meta.update({'duration': '45'})
                elif i['duration'] == '0': meta.update({'duration': '45'})
                try: meta.update({'duration': str(int(meta['duration']) * 60)})
                except: pass
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                except: pass
                try: meta.update({'year': re.findall('(\d{4})', i['premiered'])[0]})
                except: pass
                try: meta.update({'title': i['label']})
                except: pass

                try: meta.update({'tvshowyear': i['year']}) # Kodi uses the year (the year the show started) as the year for the episode. Change it from the premiered date.
                except: pass

                sysmeta = urllib_parse.quote_plus(json.dumps(meta))


                url = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, tmdb, season, episode, systvshowtitle, syspremiered, sysmeta, self.systime)
                sysurl = urllib_parse.quote_plus(url)

                path = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s' % (sysaddon, systitle, year, imdb, tmdb, season, episode, systvshowtitle, syspremiered)

                if isFolder == True:
                    url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&season=%s&episode=%s' % (sysaddon, systvshowtitle, year, imdb, tmdb, season, episode)


                cm = []

                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                if multi == True:
                    cm.append((tvshowBrowserMenu, 'Container.Update(%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s,return)' % (sysaddon, systvshowtitle, year, imdb, tmdb)))

                try:
                    overlay = int(playcount.getEpisodeOverlay(indicators, imdb, tmdb, season, episode))
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=episodePlaycount&imdb=%s&tmdb=%s&season=%s&episode=%s&query=6)' % (sysaddon, imdb, tmdb, season, episode)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=episodePlaycount&imdb=%s&tmdb=%s&season=%s&episode=%s&query=7)' % (sysaddon, imdb, tmdb, season, episode)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass

                if traktCredentials == True:
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, systvshowtitle, tmdb)))

                if isFolder == False:
                    cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))

                if isOld == True:
                    cm.append((infoMenu, 'Action(Info)'))

                cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, systvshowtitle, year, imdb, tmdb)))

                cm.append((clearProviders, 'RunPlugin(%s?action=clearCacheProviders)' % sysaddon))

                try: item = control.item(label=label, offscreen=True)
                except: item = control.item(label=label)

                art = {}

                poster = meta.get('poster', '') or addonPoster

                fanart = meta.get('fanart', '') or addonFanart

                banner = meta.get('banner', '') or fanart

                thumb = meta.get('thumb', '') or fanart

                meta.update({'poster': poster, 'fanart': fanart, 'banner': banner})
                art.update({'icon': thumb, 'thumb': thumb, 'banner': banner, 'poster': thumb, 'tvshow.poster': poster, 'season.poster': poster})

                if settingFanart == 'true':
                    art.update({'fanart': fanart})
                elif not addonFanart == None:
                    art.update({'fanart': addonFanart})

                castwiththumb = i.get('castwiththumb', []) or []
                cast = i.get('cast', []) or []
                try: item.setCast(castwiththumb)
                except: meta.update({'cast': cast})
                item.setArt(art)
                item.addContextMenuItems(cm)
                item.setProperty('IsPlayable', isPlayable)

                offset = bookmarks.get('episode', imdb, season, episode, True)
                #log_utils.log('offset: ' + str(offset))
                if float(offset) > 120:
                    percentPlayed = int(float(offset) / float(meta['duration']) * 100)
                    #log_utils.log('percentPlayed: ' + str(percentPlayed))
                    item.setProperty('resumetime', str(offset))
                    item.setProperty('percentplayed', str(percentPlayed))

                item.setInfo(type='Video', infoLabels = control.metadataClean(meta))

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
            except:
                # failure = traceback.format_exc()
                # log_utils.log('ep_dir Exception: ' + str(failure))
                pass

        control.content(syshandle, 'episodes')
        control.directory(syshandle, cacheToDisc=True)
        views.setView('episodes', {'skin.estuary': 55, 'skin.confluence': 504})


    def addDirectory(self, items, queue=False):
        if items == None or len(items) == 0: control.idle() ; sys.exit()

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        addonFanart, addonThumb, artPath = control.addonFanart(), control.addonThumb(), control.artPath()

        queueMenu = control.lang(32065)

        for i in items:
            try:
                name = i['name']

                if i['image'].startswith('http'): thumb = i['image']
                elif not artPath == None: thumb = os.path.join(artPath, i['image'])
                else: thumb = addonThumb

                url = '%s?action=%s' % (sysaddon, i['action'])
                try: url += '&url=%s' % urllib_parse.quote_plus(i['url'])
                except: pass

                cm = []

                if queue == True:
                    cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try: item = control.item(label=name, offscreen=True)
                except: item = control.item(label=name)


                item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': addonFanart})

                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                pass

        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)

