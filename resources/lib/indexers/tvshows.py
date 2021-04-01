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
from resources.lib.modules import cleantitle
from resources.lib.modules import cleangenre
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules import cache
from resources.lib.modules import metacache
from resources.lib.modules import playcount
from resources.lib.modules import workers
from resources.lib.modules import views
from resources.lib.modules import utils
from resources.lib.modules import api_keys
from resources.lib.modules import log_utils
from resources.lib.indexers import navigator

import os,sys,re,datetime
import simplejson as json

import six
from six.moves import urllib_parse, zip

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

import requests

params = dict(urllib_parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()

action = params.get('action')

class tvshows:
    def __init__(self):
        self.list = []

        self.imdb_link = 'https://www.imdb.com'
        self.trakt_link = 'https://api.trakt.tv'
        self.tvmaze_link = 'https://www.tvmaze.com'
        self.tmdb_link = 'https://api.themoviedb.org/3'
        self.logo_link = 'https://i.imgur.com/'
        self.datetime = datetime.datetime.utcnow()# - datetime.timedelta(hours = 5)
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.showunaired = control.setting('showunaired') or 'true'
        self.hq_artwork = control.setting('hq.artwork') or 'false'
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.fanart_tv_user = control.setting('fanart.tv.user')
        self.user = control.setting('fanart.tv.user') + str('')
        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.lang = control.apiLanguage()['tmdb'] or 'en'

        self.tm_user = control.setting('tm.user') or api_keys.tmdb_key
        self.tmdb_api_link = 'https://api.themoviedb.org/3/tv/%s?api_key=%s&language=%s&append_to_response=aggregate_credits,content_ratings,external_ids' % ('%s', self.tm_user, self.lang)
        self.tmdb_by_imdb = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', self.tm_user)
        self.tmdb_networks_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&sort_by=popularity.desc&with_networks=%s&page=1' % (self.tm_user, '%s')
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'

        self.search_link = 'https://api.trakt.tv/search/show?limit=20&page=1&query='
        self.tvmaze_info_link = 'https://api.tvmaze.com/shows/%s'
        self.fanart_tv_art_link = 'http://webservice.fanart.tv/v3/tv/%s'
        self.fanart_tv_level_link = 'http://webservice.fanart.tv/v3/level'

        self.persons_link = 'https://www.imdb.com/search/name?count=100&name='
        self.personlist_link = 'https://www.imdb.com/search/name?count=100&gender=male,female'
        self.popular_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&num_votes=100,&release_date=,date[0]&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.airing_link = 'https://www.imdb.com/search/title?title_type=tv_episode&release_date=date[1],date[0]&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.active_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&num_votes=10,&production_status=active&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        #self.premiere_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&languages=en&num_votes=10,&release_date=date[60],date[0]&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.premiere_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&languages=en&num_votes=10,&release_date=date[60],date[0]&sort=release_date,desc&count=%s&start=1' % self.items_per_page
        self.rating_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&num_votes=5000,&release_date=,date[0]&sort=user_rating,desc&count=%s&start=1' % self.items_per_page
        self.views_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&num_votes=100,&release_date=,date[0]&sort=num_votes,desc&count=%s&start=1' % self.items_per_page
        self.person_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&release_date=,date[0]&role=%s&sort=year,desc&count=%s&start=1' % ('%s', self.items_per_page)
        self.genre_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&release_date=,date[0]&genres=%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.keyword_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&release_date=,date[0]&keywords=%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.language_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&num_votes=100,&production_status=released&primary_language=%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.certification_link = 'https://www.imdb.com/search/title?title_type=tvSeries,tvMiniSeries&release_date=,date[0]&certificates=us:%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.trending_link = 'https://api.trakt.tv/shows/trending?limit=%s&page=1' % self.items_per_page

        self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
        self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000'
        self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items'
        self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/shows'
        self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/shows'
        self.traktfeatured_link = 'https://api.trakt.tv/recommendations/shows?limit=40'

        self.imdblists_link = 'https://www.imdb.com/user/ur%s/lists?tab=all&sort=modified&order=desc&filter=titles' % self.imdb_user
        self.imdblist_link = 'https://www.imdb.com/list/%s/?view=detail&sort=date_added,desc&title_type=tvSeries,tvMiniSeries&start=1'
        self.imdblist2_link = 'https://www.imdb.com/list/%s/?view=detail&sort=alpha,asc&title_type=tvSeries,tvMiniSeries&start=1'
        self.imdbwatchlist2_link = 'https://www.imdb.com/user/ur%s/watchlist?sort=alpha,asc' % self.imdb_user
        self.imdbwatchlist_link = 'https://www.imdb.com/user/ur%s/watchlist?sort=date_added,desc' % self.imdb_user

######## TV Show Mosts ########
        self.played1_link = 'https://api.trakt.tv/shows/played/weekly?limit=%s&page=1' % self.items_per_page
        self.played2_link = 'https://api.trakt.tv/shows/played/monthly?limit=%s&page=1' % self.items_per_page
        self.played3_link = 'https://api.trakt.tv/shows/played/yearly?limit=%s&page=1' % self.items_per_page
        self.played4_link = 'https://api.trakt.tv/shows/played/all?limit=%s&page=1' % self.items_per_page
        self.collected1_link = 'https://api.trakt.tv/shows/collected/weekly?limit=%s&page=1' % self.items_per_page
        self.collected2_link = 'https://api.trakt.tv/shows/collected/monthly?limit=%s&page=1' % self.items_per_page
        self.collected3_link = 'https://api.trakt.tv/shows/collected/yearly?limit=%s&page=1' % self.items_per_page
        self.collected4_link = 'https://api.trakt.tv/shows/collected/all?limit=%s&page=1' % self.items_per_page
        self.watched1_link = 'https://api.trakt.tv/shows/watched/weekly?limit=%s&page=1' % self.items_per_page
        self.watched2_link = 'https://api.trakt.tv/shows/watched/monthly?limit=%s&page=1' % self.items_per_page
        self.watched3_link = 'https://api.trakt.tv/shows/watched/yearly?limit=%s&page=1' % self.items_per_page
        self.watched4_link = 'https://api.trakt.tv/shows/watched/all?limit=%s&page=1' % self.items_per_page
######## /TV Show Mosts ########


    def get(self, url, idx=True, create_directory=True):
        try:
            try: url = getattr(self, url + '_link')
            except: pass

            try: u = urllib_parse.urlparse(url).netloc.lower()
            except: pass


            if u in self.trakt_link and '/users/' in url:
                try:
                    if not '/users/me/' in url: raise Exception()
                    if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user): raise Exception()
                    self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                except:
                    self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)

                if '/users/me/' in url and '/collection/' in url:
                    self.list = sorted(self.list, key=lambda k: utils.title_key(k['title']))

                if idx == True: self.worker()

            elif u in self.trakt_link and self.search_link in url:
                self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)
                if idx == True: self.worker(level=0)

            elif u in self.trakt_link:
                self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                if idx == True: self.worker()

            elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
                self.list = cache.get(self.imdb_list, 0, url)
                if idx == True: self.worker()

            elif u in self.imdb_link:
                self.list = cache.get(self.imdb_list, 24, url)
                if idx == True: self.worker()

            elif u in self.tvmaze_link:
                self.list = cache.get(self.tvmaze_list, 168, url)
                if idx == True: self.worker()

            elif u in self.tmdb_link:
                self.list = cache.get(self.tmdb_list, 24, url)
                if idx == True: self.worker()

            if idx == True and create_directory == True: self.tvshowDirectory(self.list)
            return self.list
        except:
            log_utils.log('tv_get', 1)
            pass


    def search(self):

        navigator.navigator().addDirectoryItem(32603, 'tvSearchnew', 'search.png', 'DefaultTVShows.png')

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.executescript("CREATE TABLE IF NOT EXISTS tvshow (ID Integer PRIMARY KEY AUTOINCREMENT, term);")
        except:
            pass

        dbcur.execute("SELECT * FROM tvshow ORDER BY ID DESC")

        lst = []

        delete_option = False
        for (id,term) in dbcur.fetchall():
            if term not in str(lst):
                delete_option = True
                navigator.navigator().addDirectoryItem(term.title(), 'tvSearchterm&name=%s' % term, 'search.png', 'DefaultTVShows.png')
                lst += [(term)]
        dbcur.close()

        if delete_option:
            navigator.navigator().addDirectoryItem(32605, 'clearCacheSearch&select=tvshow', 'tools.png', 'DefaultAddonProgram.png')

        navigator.navigator().endDirectory(False)


    def search_new(self):
        control.idle()

        t = control.lang(32010)
        k = control.keyboard('', t) ; k.doModal()
        q = k.getText() if k.isConfirmed() else None

        if (q == None or q == ''): return
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM tvshow WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO tvshow VALUES (?,?)", (None,q))
        dbcon.commit()
        dbcur.close()
        url = self.search_link + urllib_parse.quote_plus(q)
        if control.getKodiVersion() >= 18:
            self.get(url)
        else:
            url = '%s?action=tvshowPage&url=%s' % (sys.argv[0], urllib_parse.quote_plus(url))
            control.execute('Container.Update(%s)' % url)


    def search_term(self, q):
        control.idle()
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM tvshow WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO tvshow VALUES (?,?)", (None, q))
        dbcon.commit()
        dbcur.close()
        url = self.search_link + urllib_parse.quote_plus(q)
        if control.getKodiVersion() >= 18:
            self.get(url)
        else:
            url = '%s?action=tvshowPage&url=%s' % (sys.argv[0], urllib_parse.quote_plus(url))
            control.execute('Container.Update(%s)' % url)


    def person(self):
        try:
            control.idle()

            t = control.lang(32010)
            k = control.keyboard('', t) ; k.doModal()
            q = k.getText() if k.isConfirmed() else None

            if (q == None or q == ''): return

            url = self.persons_link + urllib_parse.quote_plus(q)
            if control.getKodiVersion() >= 18:
                self.persons(url)
            else:
                url = '%s?action=tvPersons&url=%s' % (sys.argv[0], urllib_parse.quote_plus(url))
                control.execute('Container.Update(%s)' % url)
        except:
            return


    def genres(self):
        genres = [
            ('Action', 'action', True),
            ('Adventure', 'adventure', True),
            ('Animation', 'animation', True),
            ('Anime', 'anime', False),
            ('Biography', 'biography', True),
            ('Comedy', 'comedy', True),
            ('Crime', 'crime', True),
            ('Drama', 'drama', True),
            ('Family', 'family', True),
            ('Fantasy', 'fantasy', True),
            ('Game-Show', 'game_show', True),
            ('History', 'history', True),
            ('Horror', 'horror', True),
            ('Music ', 'music', True),
            ('Musical', 'musical', True),
            ('Mystery', 'mystery', True),
            ('News', 'news', True),
            ('Reality-TV', 'reality_tv', True),
            ('Romance', 'romance', True),
            ('Science Fiction', 'sci_fi', True),
            ('Sport', 'sport', True),
            ('Talk-Show', 'talk_show', True),
            ('Thriller', 'thriller', True),
            ('War', 'war', True),
            ('Western', 'western', True)
        ]

        for i in genres: self.list.append(
            {
                'name': cleangenre.lang(i[0], self.lang),
                'url': self.genre_link % i[1] if i[2] else self.keyword_link % i[1],
                'image': 'genres.png',
                'action': 'tvshows'
            })

        self.addDirectory(self.list)
        return self.list


    def networks(self):
        networks = [
            ('A&E', '129', 'https://i.imgur.com/xLDfHjH.png'),
            ('ABC', '2', 'https://i.imgur.com/qePLxos.png'),
            ('Acorn TV', '2697', 'https://i.imgur.com/fSWB5gB.png'),
            ('Adult Swim', '80', 'https://i.imgur.com/jCqbRcS.png'),
            ('Amazon', '1024', 'https://i.imgur.com/ru9DDlL.png'),
            ('AMC', '174', 'https://i.imgur.com/ndorJxi.png'),
            ('Animal Planet', '91', 'https://i.imgur.com/olKc4RP.png'),
            ('Apple TV+', '2552', 'https://i.imgur.com/fAQMVNp.png'),
            ('AT-X', '173', 'https://i.imgur.com/JshJYGN.png'),
            ('Audience', '251', 'https://i.imgur.com/5Q3mo5A.png'),
            ('BBC One', '4', 'https://i.imgur.com/u8x26te.png'),
            ('BBC Two', '332', 'https://i.imgur.com/SKeGH1a.png'),
            ('BBC Three', '3', 'https://i.imgur.com/SDLeLcn.png'),
            ('BBC Four', '100', 'https://i.imgur.com/PNDalgw.png'),
            ('BBC America', '493', 'https://i.imgur.com/TUHDjfl.png'),
            ('BET', '24', 'https://i.imgur.com/ZpGJ5UQ.png'),
            ('Bravo', '74', 'https://i.imgur.com/TmEO3Tn.png'),
            ('Cartoon Network', '56', 'https://i.imgur.com/zmOLbbI.png'),
            ('CBC', '23', 'https://i.imgur.com/unQ7WCZ.png'),
            ('CBS All Access', '1709', 'https://i.imgur.com/ZvaWMuU.png'),
            ('CBS', '16', 'https://i.imgur.com/8OT8igR.png'),
            ('Channel 4', '26', 'https://i.imgur.com/6ZA9UHR.png'),
            ('Channel 5', '99', 'https://i.imgur.com/5ubnvOh.png'),
            ('Cinemax', '359', 'https://i.imgur.com/zWypFNI.png'),
            ('Comedy Central', '47', 'https://i.imgur.com/ko6XN77.png'),
            ('Crackle', '928', 'https://i.imgur.com/53kqZSY.png'),
            ('CTV', '110', 'https://i.imgur.com/qUlyVHz.png'),
            ('DC Universe', '2243', 'https://i.imgur.com/bhWIubn.png'),
            ('Discovery Channel', '64', 'https://i.imgur.com/8UrXnAB.png'),
            ('Disney+', '2739', 'https://i.imgur.com/DVrPgbM.png'),
            ('Disney Channel', '54', 'https://i.imgur.com/ZCgEkp6.png'),
            ('Disney XD', '44', 'https://i.imgur.com/PAJJoqQ.png'),
            ('E!', '76', 'https://i.imgur.com/3Delf9f.png'),
            ('E4', '136', 'https://i.imgur.com/frpunK8.png'),
            ('Epix', '922', 'https://i.imgur.com/XcuclbM.png'),
            ('FOX', '19', 'https://i.imgur.com/6vc0Iov.png'),
            ('Freeform', '1267', 'https://i.imgur.com/f9AqoHE.png'),
            ('Hallmark Channel', '384', 'https://i.imgur.com/zXS64I8.png'),
            ('HBO Max', '3186', 'https://i.imgur.com/mmRMG75.png'),
            ('HBO', '49', 'https://i.imgur.com/Hyu8ZGq.png'),
            ('HGTV', '210', 'https://i.imgur.com/INnmgLT.png'),
            ('History Channel', '65', 'https://i.imgur.com/LEMgy6n.png'),
            ('Hulu', '453', 'https://i.imgur.com/cLVo7NH.png'),
            ('ITV', '9', 'https://i.imgur.com/5Hxp5eA.png'),
            ('Lifetime', '34', 'https://i.imgur.com/tvYbhen.png'),
            ('MTV', '33', 'https://i.imgur.com/QM6DpNW.png'),
            ('National Geographic', '43', 'https://i.imgur.com/XCGNKVQ.png'),
            ('NBC', '6', 'https://i.imgur.com/yPRirQZ.png'),
            ('Netflix', '213', 'https://i.imgur.com/02VN1wq.png'),
            ('Nick Junior', '35', 'https://i.imgur.com/leuCWYt.png'),
            ('Nickelodeon', '13', 'https://i.imgur.com/OUVoqYc.png'),
            ('Paramount Network', '2076', 'https://i.imgur.com/oEz8xLB.png'),
            ('PBS', '14', 'https://i.imgur.com/r9qeDJY.png'),
            ('Showtime', '67', 'https://i.imgur.com/SawAYkO.png'),
            ('Sky Atlantic', '1063', 'https://i.imgur.com/9u6M0ef.png'),
            ('Sky One', '214', 'https://i.imgur.com/xbgzhPU.png'),
            ('Spike', '55', 'https://i.imgur.com/BhXYytR.png'),
            ('Starz', '318', 'https://i.imgur.com/Z0ep2Ru.png'),
            ('SundanceTV', '270', 'https://i.imgur.com/qldG5p2.png'),
            ('Syfy', '77', 'https://i.imgur.com/9yCq37i.png'),
            ('TBS', '68', 'https://i.imgur.com/RVCtt4Z.png'),
            ('The CW', '71', 'https://i.imgur.com/Q8tooeM.png'),
            ('The WB', '21', 'https://i.imgur.com/rzfVME6.png'),
            ('TLC', '84', 'https://i.imgur.com/c24MxaB.png'),
            ('TNT', '41', 'https://i.imgur.com/WnzpAGj.png'),
            ('Travel Channel', '209', 'https://i.imgur.com/mWXv7SF.png'),
            ('truTV', '364', 'https://i.imgur.com/HnB3zfc.png'),
            ('TV Land', '397', 'https://i.imgur.com/1nIeDA5.png'),
            ('USA Network', '30', 'https://i.imgur.com/Doccw9E.png'),
            ('VH1', '158', 'https://i.imgur.com/IUtHYzA.png'),
            ('WGN America', '202', 'https://i.imgur.com/TL6MzgO.png'),
            ('YouTube Premium', '1436', 'https://i.imgur.com/9xpox47.png')
        ]

        for i in networks: self.list.append({'name': i[0], 'url': self.tmdb_networks_link % i[1], 'image': i[2], 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list


    # def networks2(self): # TVMaze Networks
        # networks = [
            # ('A&E', '/shows?Show[network_id]=29&page=1', 'https://i.imgur.com/xLDfHjH.png'),
            # ('ABC', '/shows?Show[network_id]=3&page=1', 'https://i.imgur.com/qePLxos.png'),
            # ('AMC', '/shows?Show[network_id]=20&page=1', 'https://i.imgur.com/ndorJxi.png'),
            # ('AT-X', '/shows?Show[network_id]=167&page=1', 'https://i.imgur.com/JshJYGN.png'),
            # ('Adult Swim', '/shows?Show[network_id]=10&page=1', 'https://i.imgur.com/jCqbRcS.png'),
            # ('Amazon', '/shows?Show[webChannel_id]=3&page=1', 'https://i.imgur.com/ru9DDlL.png'),
            # ('Animal Planet', '/shows?Show[network_id]=92&page=1', 'https://i.imgur.com/olKc4RP.png'),
            # ('Apple TV+', '/shows?Show[webChannel_id]=310&page=1', 'https://i.imgur.com/3baZigT.png'),
            # ('Audience', '/shows?Show[network_id]=31&page=1', 'https://i.imgur.com/5Q3mo5A.png'),
            # ('BBC America', '/shows?Show[network_id]=15&page=1', 'https://i.imgur.com/TUHDjfl.png'),
            # ('BBC One', '/shows?Show[network_id]=12&page=1', 'https://i.imgur.com/u8x26te.png'),
            # ('BBC Two', '/shows?Show[network_id]=37&page=1', 'https://i.imgur.com/SKeGH1a.png'),
            # ('BBC Three', '/shows?Show[network_id]=71&page=1', 'https://i.imgur.com/SDLeLcn.png'),
            # ('BBC Four', '/shows?Show[network_id]=51&page=1', 'https://i.imgur.com/PNDalgw.png'),
            # ('BET', '/shows?Show[network_id]=56&page=1', 'https://i.imgur.com/ZpGJ5UQ.png'),
            # ('Bravo', '/shows?Show[network_id]=52&page=1', 'https://i.imgur.com/TmEO3Tn.png'),
            # ('CBC', '/shows?Show[network_id]=36&page=1', 'https://i.imgur.com/unQ7WCZ.png'),
            # ('CBS', '/shows?Show[network_id]=2&page=1', 'https://i.imgur.com/8OT8igR.png'),
            # ('CNBC', '/shows?Show[network_id]=93&page=1', 'https://i.imgur.com/PoXLjlU.png'),
            # ('CTV', '/shows?Show[network_id]=48&page=1', 'https://i.imgur.com/qUlyVHz.png'),
            # ('CW', '/shows?Show[network_id]=5&page=1', 'https://i.imgur.com/Q8tooeM.png'),
            # ('CW Seed', '/shows?Show[webChannel_id]=13&page=1', 'https://i.imgur.com/nOdKoEy.png'),
            # ('Cartoon Network', '/shows?Show[network_id]=11&page=1', 'https://i.imgur.com/zmOLbbI.png'),
            # ('Channel 4', '/shows?Show[network_id]=45&page=1', 'https://i.imgur.com/6ZA9UHR.png'),
            # ('Channel 5', '/shows?Show[network_id]=135&page=1', 'https://i.imgur.com/5ubnvOh.png'),
            # ('Cinemax', '/shows?Show[network_id]=19&page=1', 'https://i.imgur.com/zWypFNI.png'),
            # ('Comedy Central', '/shows?Show[network_id]=23&page=1', 'https://i.imgur.com/ko6XN77.png'),
            # ('Crackle', '/shows?Show%5BwebChannel_id%5D=4&page=1', 'https://i.imgur.com/53kqZSY.png'),
            # ('CuriosityStream', '/shows?Show[webChannel_id]=188&page=1', 'https://i.imgur.com/Lyde6b9.png'),
            # ('Discovery Channel', '/shows?Show[network_id]=66&page=1', 'https://i.imgur.com/8UrXnAB.png'),
            # ('Discovery ID', '/shows?Show[network_id]=89&page=1', 'https://i.imgur.com/07w7BER.png'),
            # ('Disney+', '/shows?Show[webChannel_id]=287&page=1', 'https://i.imgur.com/DVrPgbM.png'),
            # ('Disney Channel', '/shows?Show[network_id]=78&page=1', 'https://i.imgur.com/ZCgEkp6.png'),
            # ('Disney XD', '/shows?Show[network_id]=25&page=1', 'https://i.imgur.com/PAJJoqQ.png'),
            # ('E! Entertainment', '/shows?Show[network_id]=43&page=1', 'https://i.imgur.com/3Delf9f.png'),
            # ('E4', '/shows?Show[network_id]=41&page=1', 'https://i.imgur.com/frpunK8.png'),
            # ('FOX', '/shows?Show[network_id]=4&page=1', 'https://i.imgur.com/6vc0Iov.png'),
            # ('FX', '/shows?Show[network_id]=13&page=1', 'https://i.imgur.com/aQc1AIZ.png'),
            # ('Freeform', '/shows?Show[network_id]=26&page=1', 'https://i.imgur.com/f9AqoHE.png'),
            # ('HBO', '/shows?Show[network_id]=8&page=1', 'https://i.imgur.com/Hyu8ZGq.png'),
            # ('HBO Max', '/shows?Show[webChannel_id]=329&page=1', 'https://i.imgur.com/r7dwKMB.png'),
            # ('HGTV', '/shows?Show[network_id]=192&page=1', 'https://i.imgur.com/INnmgLT.png'),
            # ('Hallmark', '/shows?Show[network_id]=50&page=1', 'https://i.imgur.com/zXS64I8.png'),
            # ('History Channel', '/shows?Show[network_id]=53&page=1', 'https://i.imgur.com/LEMgy6n.png'),
            # ('Hulu', '/shows?Show[webChannel_id]=2&page=1', 'https://i.imgur.com/cLVo7NH.png'),
            # ('ITV', '/shows?Show[network_id]=35&page=1', 'https://i.imgur.com/5Hxp5eA.png'),
            # ('Lifetime', '/shows?Show[network_id]=18&page=1', 'https://i.imgur.com/tvYbhen.png'),
            # ('MTV', '/shows?Show[network_id]=22&page=1', 'https://i.imgur.com/QM6DpNW.png'),
            # ('NBC', '/shows?Show[network_id]=1&page=1', 'https://i.imgur.com/yPRirQZ.png'),
            # ('National Geographic', '/shows?Show[network_id]=42&page=1', 'https://i.imgur.com/XCGNKVQ.png'),
            # ('Netflix', '/shows?Show[webChannel_id]=1&page=1', 'https://i.imgur.com/02VN1wq.png'),
            # ('Nickelodeon', '/shows?Show[network_id]=27&page=1', 'https://i.imgur.com/OUVoqYc.png'),
            # ('Oxygen', '/shows?Show[network_id]=79&page=1', 'https://i.imgur.com/YEk9T70.png'),
            # ('PBS', '/shows?Show[network_id]=85&page=1', 'https://i.imgur.com/r9qeDJY.png'),
            # ('Showtime', '/shows?Show[network_id]=9&page=1', 'https://i.imgur.com/SawAYkO.png'),
            # ('Sky1', '/shows?Show[network_id]=63&page=1', 'https://i.imgur.com/xbgzhPU.png'),
            # ('Sky Go', '/shows?Show[webChannel_id]=117&Show[sort]=1&page=1', 'https://i.imgur.com/rNkffls.png'),
            # ('Starz', '/shows?Show[network_id]=17&page=1', 'https://i.imgur.com/Z0ep2Ru.png'),
            # ('Sundance', '/shows?Show[network_id]=33&page=1', 'https://i.imgur.com/qldG5p2.png'),
            # ('Syfy', '/shows?Show[network_id]=16&page=1', 'https://i.imgur.com/9yCq37i.png'),
            # ('TBS', '/shows?Show[network_id]=32&page=1', 'https://i.imgur.com/RVCtt4Z.png'),
            # ('TLC', '/shows?Show[network_id]=80&page=1', 'https://i.imgur.com/c24MxaB.png'),
            # ('TNT', '/shows?Show[network_id]=14&page=1', 'https://i.imgur.com/WnzpAGj.png'),
            # ('TV Land', '/shows?Show[network_id]=57&page=1', 'https://i.imgur.com/1nIeDA5.png'),
            # ('Travel Channel', '/shows?Show[network_id]=82&page=1', 'https://i.imgur.com/mWXv7SF.png'),
            # ('TruTV', '/shows?Show[network_id]=84&page=1', 'https://i.imgur.com/HnB3zfc.png'),
            # ('USA', '/shows?Show[network_id]=30&page=1', 'https://i.imgur.com/Doccw9E.png'),
            # ('VH1', '/shows?Show[network_id]=55&page=1', 'https://i.imgur.com/IUtHYzA.png'),
            # ('Viceland', '/shows?Show[network_id]=1006&page=1', 'https://i.imgur.com/rNZ9yOv.png'),
            # ('WGN', '/shows?Show[network_id]=28&page=1', 'https://i.imgur.com/TL6MzgO.png'),
            # ('YouTube Premium', '/shows?Show[webChannel_id]=43&page=1', 'https://i.imgur.com/9xpox47.png')
        # ]

        # for i in networks: self.list.append({'name': i[0], 'url': self.tvmaze_link + i[1], 'image': i[2], 'action': 'tvshows'})
        # self.addDirectory(self.list)
        # return self.list


    def languages(self):
        languages = [
            ('Arabic', 'ar'),
            ('Bosnian', 'bs'),
            ('Bulgarian', 'bg'),
            ('Chinese', 'zh'),
            ('Croatian', 'hr'),
            ('Dutch', 'nl'),
            ('English', 'en'),
            ('Finnish', 'fi'),
            ('French', 'fr'),
            ('German', 'de'),
            ('Greek', 'el'),
            ('Hebrew', 'he'),
            ('Hindi ', 'hi'),
            ('Hungarian', 'hu'),
            ('Icelandic', 'is'),
            ('Italian', 'it'),
            ('Japanese', 'ja'),
            ('Korean', 'ko'),
            ('Norwegian', 'no'),
            ('Persian', 'fa'),
            ('Polish', 'pl'),
            ('Portuguese', 'pt'),
            ('Punjabi', 'pa'),
            ('Romanian', 'ro'),
            ('Russian', 'ru'),
            ('Serbian', 'sr'),
            ('Spanish', 'es'),
            ('Swedish', 'sv'),
            ('Turkish', 'tr'),
            ('Ukrainian', 'uk')
        ]

        for i in languages: self.list.append({'name': str(i[0]), 'url': self.language_link % i[1], 'image': 'languages.png', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list


    def certifications(self):
        certificates = ['TV-G', 'TV-PG', 'TV-14', 'TV-MA']

        for i in certificates: self.list.append({'name': str(i), 'url': self.certification_link % str(i), 'image': 'certificates.png', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list


    def persons(self, url):
        if url == None:
            self.list = cache.get(self.imdb_person_list, 24, self.personlist_link)
        else:
            self.list = cache.get(self.imdb_person_list, 1, url)

        for i in list(range(0, len(self.list))): self.list[i].update({'action': 'tvshows'})
        self.addDirectory(self.list)
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
            if self.imdb_user == '': raise Exception()
            userlists += cache.get(self.imdb_user_list, 0, self.imdblists_link)
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
        for i in list(range(0, len(self.list))):
            self.list[i].update({'action': 'tvshows'})
        self.list = sorted(self.list, key=lambda k: (k['image'], k['name'].lower()))
        self.addDirectory(self.list)
        return self.list


    def trakt_list(self, url, user):
        try:
            dupes = []

            q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib_parse.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q

            result = trakt.getTraktAsJson(u)

            items = []
            for i in result:
                try: items.append(i['show'])
                except: pass
            if len(items) == 0:
                items = result
        except:
            return

        try:
            q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
            if not int(q['limit']) == len(items): raise Exception()
            q.update({'page': str(int(q['page']) + 1)})
            q = (urllib_parse.urlencode(q)).replace('%2C', ',')
            next = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q
            next = six.ensure_str(next)
        except:
            next = ''

        #for item in items:
        def items_list(item):
            try:
                title = item['title']
                title = re.sub('\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)

                year = item['year']
                year = re.sub('[^0-9]', '', str(year))

                #if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = item['ids']['imdb']
                if imdb == None or imdb == '': imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tmdb = item['ids']['tmdb']
                if tmdb == None or tmdb == '': tmdb = '0'
                tmdb = str(tmdb)

                tvdb = item['ids']['tvdb']
                tvdb = re.sub('[^0-9]', '', str(tvdb))

                #if tvdb == None or tvdb == '' or tvdb in dupes: raise Exception()
                if tvdb in dupes: raise Exception()
                dupes.append(tvdb)

                try: premiered = item['first_aired']
                except: premiered = '0'
                try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                except: premiered = '0'

                try: studio = item['network']
                except: studio = '0'
                if studio == None: studio = '0'

                try: genre = item['genres']
                except: genre = '0'
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)

                try: duration = str(item['runtime'])
                except: duration = '0'
                if duration == None: duration = '0'

                try: rating = str(item['rating'])
                except: rating = '0'
                if rating == None or rating == '0.0': rating = '0'

                try: votes = str(item['votes'])
                except: votes = '0'
                try: votes = str(format(int(votes),',d'))
                except: pass
                if votes == None: votes = '0'

                try: mpaa = item['certification']
                except: mpaa = '0'
                if mpaa == None: mpaa = '0'

                try: plot = item['overview']
                except: plot = '0'
                if plot == None: plot = '0'
                plot = client.replaceHTMLCodes(plot)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration,
                                  'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'poster': '0', 'next': next})
            except:
                log_utils.log('trakt_list0', 1)
                pass

        try:
            threads = []
            for i in items: threads.append(workers.Thread(items_list, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            return self.list
        except:
            log_utils.log('trakt_list1', 1)
            return


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

                self.list.append({'name': name, 'url': url, 'context': url, 'image': 'trakt.png'})
            except:
                pass

        return self.list


    def imdb_list(self, url):
        try:
            dupes = []

            for i in re.findall('date\[(\d+)\]', url):
                url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days = int(i))).strftime('%Y-%m-%d'))

            def imdb_watchlist_id(url):
                return client.parseDOM(client.request(url), 'meta', ret='content', attrs = {'property': 'pageId'})[0]

            if url == self.imdbwatchlist_link:
                url = cache.get(imdb_watchlist_id, 8640, url)
                url = self.imdblist_link % url

            elif url == self.imdbwatchlist2_link:
                url = cache.get(imdb_watchlist_id, 8640, url)
                url = self.imdblist2_link % url

            result = client.request(url)
            result = control.six_decode(result)

            result = result.replace('\n', ' ')

            items = client.parseDOM(result, 'div', attrs = {'class': 'lister-item .*?'})
            items += client.parseDOM(result, 'div', attrs = {'class': 'list_item.*?'})
        except:
            return

        try:
            result = result.replace(r'"class=".*?ister-page-nex', '" class="lister-page-nex')
            next = client.parseDOM(result, 'a', ret='href', attrs = {'class': r'.*?ister-page-nex.*?'})

            if len(next) == 0:
                next = client.parseDOM(result, 'div', attrs = {'class': u'pagination'})[0]
                next = zip(client.parseDOM(next, 'a', ret='href'), client.parseDOM(next, 'a'))
                next = [i[0] for i in next if 'Next' in i[1]]

            next = url.replace(urllib_parse.urlparse(url).query, urllib_parse.urlparse(next[0]).query)
            next = client.replaceHTMLCodes(next)
            next = six.ensure_str(next)
        except:
            next = ''

        for item in items:
            try:
                title = client.parseDOM(item, 'a')[1]
                title = client.replaceHTMLCodes(title)
                title = six.ensure_str(title)

                year = client.parseDOM(item, 'span', attrs = {'class': r'lister-item-year.*?'})
                year += client.parseDOM(item, 'span', attrs = {'class': r'year_type'})
                try: year = re.findall(r'(\d{4})', str(year)[0])[0]
                except: year = '0'
                year = six.ensure_str(year)

                #if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = client.parseDOM(item, 'a', ret='href')[0]
                imdb = re.findall('(tt\d*)', imdb)[0]
                imdb = six.ensure_str(imdb)

                if imdb in dupes: raise Exception()
                dupes.append(imdb)

                try: poster = client.parseDOM(item, 'img', ret='loadlate')[0]
                except: poster = '0'
                if '/nopicture/' in poster or '/sash/' in poster: poster = '0'
                else:
                    poster = re.sub('(?:_SX|_SY|_UX|_UY|_CR|_AL)(?:\d+|_).+?\.', '_SX500.', poster)
                    poster = client.replaceHTMLCodes(poster)
                    poster = six.ensure_str(poster)

                rating = '0'
                try:
                    rating = client.parseDOM(item, 'span', attrs = {'class': 'rating-rating'})[0]
                    rating = client.parseDOM(rating, 'span', attrs = {'class': 'value'})[0]
                except:
                    try:
                        rating = client.parseDOM(item, 'div', ret='data-value', attrs = {'class': '.*?imdb-rating'})[0]
                    except:
                        try:
                            rating = client.parseDOM(item, 'span', attrs = {'class': '.*?_rating'})[0]
                        except:
                            pass
                if rating == '' or rating == '-':
                    rating = '0'
                rating = client.replaceHTMLCodes(rating)
                rating = six.ensure_str(rating)

                try:
                    votes = client.parseDOM(item, 'div', ret='title', attrs = {'class': '.*?rating-list'})[0]
                    votes = re.findall('\((.+?) vote(?:s|)\)', votes)[0]
                except:
                    try:
                        votes = client.parseDOM(item, 'span', ret='data-value')[0]
                    except:
                        votes = '0'
                if votes == '':
                    votes = '0'
                votes = client.replaceHTMLCodes(votes)
                votes = six.ensure_str(votes)

                plot = '0'
                try: plot = client.parseDOM(item, 'p', attrs = {'class': 'text-muted'})[0]
                except: pass
                try: plot = client.parseDOM(item, 'div', attrs = {'class': 'item_description'})[0]
                except: pass
                plot = plot.rsplit('<span>', 1)[0].strip()
                plot = re.sub('<.+?>|</.+?>', '', plot)
                if plot == '': plot = '0'
                plot = client.replaceHTMLCodes(plot)
                plot = six.ensure_str(plot)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'rating': rating, 'votes': votes, 'plot': plot, 'imdb': imdb, 'tmdb': '0', 'tvdb': '0', 'poster': poster, 'next': next})
            except:
                log_utils.log('imdb_list', 1)
                pass

        return self.list


    def imdb_person_list(self, url):
        try:
            result = client.request(url)
            items = client.parseDOM(result, 'div', attrs = {'class': '.+? mode-detail'})
        except:
            return

        for item in items:
            try:
                name = client.parseDOM(item, 'img', ret='alt')[0]
                name = client.replaceHTMLCodes(name)
                name = six.ensure_str(name)

                url = client.parseDOM(item, 'a', ret='href')[0]
                url = re.findall('(nm\d*)', url, re.I)[0]
                url = self.person_link % url
                url = client.replaceHTMLCodes(url)
                url = six.ensure_str(url)

                image = client.parseDOM(item, 'img', ret='src')[0]
                # if not ('._SX' in image or '._SY' in image): raise Exception()
                image = re.sub('(?:_SX|_SY|_UX|_UY|_CR|_AL)(?:\d+|_).+?\.', '_SX500.', image)
                image = client.replaceHTMLCodes(image)
                image = six.ensure_str(image)

                self.list.append({'name': name, 'url': url, 'image': image})
            except:
                pass

        return self.list


    def imdb_user_list(self, url):
        try:
            result = client.request(url)
            items = client.parseDOM(result, 'li', attrs = {'class': 'ipl-zebra-list__item user-list'})
        except:
            pass

        if control.setting('imdb.sort.order') == '1':
            list = self.imdblist2_link
        else:
            list = self.imdblist_link

        for item in items:
            try:
                name = client.parseDOM(item, 'a')[0]
                name = client.replaceHTMLCodes(name)
                name = six.ensure_str(name)

                url = client.parseDOM(item, 'a', ret='href')[0]
                url = url = url.split('/list/', 1)[-1].strip('/')
                url = list % url
                url = client.replaceHTMLCodes(url)
                url = six.ensure_str(url)

                self.list.append({'name': name, 'url': url, 'context': url, 'image': 'imdb.png'})
            except:
                pass

        return self.list


    def tvmaze_list(self, url):
        try:
            result = client.request(url)

            result = client.parseDOM(result, 'div', attrs = {'id': 'w1'})

            items = client.parseDOM(result, 'span', attrs = {'class': 'title'})
            items = [client.parseDOM(i, 'a', ret='href') for i in items]
            items = [i[0] for i in items if len(i) > 0]
            items = [re.findall('/(\d+)/', i) for i in items]
            items = [i[0] for i in items if len(i) > 0]

            next = ''; last = []; nextp = []
            page = int(str(url.split('&page=', 1)[1]))
            next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
            last = client.parseDOM(result, 'li', attrs = {'class': 'last disabled'})
            nextp = client.parseDOM(result, 'li', attrs = {'class': 'next'})
            if last != [] or nextp == []: next = ''
        except:
            log_utils.log('tvm-list fail', 1)
            return

        def items_list(i):
            try:
                url = self.tvmaze_info_link % i

                item = requests.get(url, timeout=10).json()

                title = item['name']
                title = re.sub('\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)
                title = six.ensure_str(title)

                premiered = item['premiered']
                try: premiered = re.findall('(\d{4}-\d{2}-\d{2})', premiered)[0]
                except: premiered = '0'
                premiered = six.ensure_str(premiered)

                year = item['premiered']
                try: year = re.findall('(\d{4})', year)[0]
                except: year = '0'
                year = six.ensure_str(year)

                #if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = item['externals']['imdb']
                if imdb == None or imdb == '': imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                imdb = six.ensure_str(imdb)

                tvdb = item['externals']['thetvdb']
                if tvdb == None or tvdb == '': tvdb = '0'
                else: tvdb = re.sub('[^0-9]', '', str(tvdb))
                tvdb = six.ensure_str(tvdb)

                try: poster = item['image']['original']
                except: poster = '0'
                if poster == None or poster == '': poster = '0'
                poster = six.ensure_str(poster)

                try: studio = item['network']['name']
                except: studio = '0'
                if studio == None: studio = '0'
                studio = six.ensure_str(studio)

                try: genre = item['genres']
                except: genre = '0'
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)
                genre = six.ensure_str(genre)

                try: duration = item['runtime']
                except: duration = '0'
                if duration == None: duration = '0'
                duration = str(duration)
                duration = six.ensure_str(duration)

                try: rating = item['rating']['average']
                except: rating = '0'
                if rating == None or rating == '0.0': rating = '0'
                rating = str(rating)
                rating = six.ensure_str(rating)

                try: plot = item['summary']
                except: plot = '0'
                if plot == None: plot = '0'
                plot = re.sub('<.+?>|</.+?>|\n', '', plot)
                plot = client.replaceHTMLCodes(plot)
                plot = six.ensure_str(plot)

                try: content = item['type'].lower()
                except: content = '0'
                if content == None or content == '': content = '0'
                content = six.ensure_str(content)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'plot': plot,
                                  'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0', 'poster': poster, 'content': content, 'next': next})
            except:
                # log_utils.log('tvmaze0', 1)
                pass

        try:
            threads = []
            for i in items: threads.append(workers.Thread(items_list, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            return self.list
        except:
            # log_utils.log('tvmaze1', 1)
            return


    def tmdb_list(self, url):
        try:
            result = requests.get(url, timeout=10).json()
            result = control.six_decode(result)
            items = result['results']
        except:
            log_utils.log('tmdb_list0', 1)
            return

        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total: raise Exception()
            if 'page=' not in url: raise Exception()
            next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
        except:
            next = ''

        for item in items:

            try:
                tmdb = str(item.get('id'))

                try: title = item['name']
                except: title = ''
                title = six.ensure_str(title)

                try: originaltitle = item['original_name']
                except: originaltitle = ''
                originaltitle = six.ensure_str(originaltitle)
                if not originaltitle: originaltitle = title

                try: rating = str(item['vote_average'])
                except: rating = ''
                if not rating: rating = '0'

                try: votes = str(item['vote_count'])
                except: votes = ''
                if not votes: votes = '0'

                try: premiered = item['first_air_date']
                except: premiered = ''
                if not premiered : premiered = '0'

                try: year = re.findall('(\d{4})', premiered)[0]
                except: year = ''
                if not year : year = '0'

                try: plot = item['overview']
                except: plot = ''
                if not plot: plot = '0'
                else: plot = client.replaceHTMLCodes(six.ensure_str(plot))

                try: poster_path = item['poster_path']
                except: poster_path = ''
                if poster_path: poster = self.tm_img_link % ('500', poster_path)
                else: poster = '0'

                self.list.append({'title': title, 'originaltitle': originaltitle, 'premiered': premiered, 'year': year, 'rating': rating, 'votes': votes, 'plot': plot, 'imdb': '0', 'tmdb': tmdb, 'tvdb': '0', 'poster': poster, 'next': next})
            except:
                log_utils.log('tmdb_list1', 1)
                pass

        return self.list

    def worker(self, level=1):
        self.meta = []
        total = len(self.list)

        self.fanart_tv_headers = {'api-key': api_keys.fanarttv_key}
        if not self.fanart_tv_user == '':
            self.fanart_tv_headers.update({'client-key': self.fanart_tv_user})

        for i in list(range(0, total)): self.list[i].update({'metacache': False})

        self.list = metacache.fetch(self.list, self.lang, self.user)

        for r in list(range(0, total, 40)):
            threads = []
            for i in list(range(r, r+40)):
                if i <= total: threads.append(workers.Thread(self.super_info, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            if self.meta: metacache.insert(self.meta)

        self.list = [i for i in self.list if not i['tmdb'] == '0']

        #if self.fanart_tv_user == '':
            #for i in self.list: i.update({'clearlogo': '', 'clearart': ''})


    def super_info(self, i):
        try:
            if self.list[i]['metacache'] == True: raise Exception()

            imdb = self.list[i]['imdb'] if 'imdb' in self.list[i] else '0'
            tmdb = self.list[i]['tmdb'] if 'tmdb' in self.list[i] else '0'
            tvdb = self.list[i]['tvdb'] if 'tvdb' in self.list[i] else '0'

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

            if imdb == '0' or tmdb == '0' or tvdb == '0':
                try:
                    ids_from_trakt = trakt.SearchTVShow(urllib_parse.quote_plus(self.list[i]['title']), self.list[i]['year'], full=False)[0]
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

            if tmdb == '0': raise Exception()

            en_url = self.tmdb_api_link % (tmdb)# + ',images'
            f_url = self.tmdb_api_link % (tmdb) + ',translations'#,images&include_image_language=en,%s,null' % self.lang
            if self.lang == 'en':
                item = requests.get(en_url, timeout=10).json()
            else:
                item = requests.get(f_url, timeout=10).json()
            item = control.six_decode(item)
            #item = requests.get(url, timeout=10).content
            #item = utils.json_loads_as_str(item)
            if item == None: raise Exception()

            if imdb == '0':
                try:
                    imdb = item['external_ids']['imdb_id']
                    if not imdb: imdb = '0'
                except:
                    imdb = '0'

            if tvdb == '0':
                try:
                    tvdb = item['external_ids']['tvdb_id']
                    if not tvdb: tvdb = '0'
                    else: tvdb = str(tvdb)
                except:
                    tvdb = '0'

            original_language = item.get('original_language', '')

            if original_language == 'en': title = item.get('original_name', '')
            else: title = item.get('name', '')
            if title: title = six.ensure_str(title)
            else: title = self.list[i]['title']

            try: label = item.get('name', '')
            except: label = ''
            if label: label = six.ensure_str(label)
            else: label = '0'

            try: premiered = item['first_air_date']
            except: premiered = ''
            if not premiered : premiered = '0'

            try: year = re.findall('(\d{4})', premiered)[0]
            except: year = ''
            if not year : year = '0'

            try: studio = item['networks'][0]['name']
            except: studio = ''
            if not studio: studio = '0'
            else: studio = six.ensure_str(studio, errors='replace')

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

            try: plot = item['overview']
            except: plot = ''
            if not plot: plot = '0'
            else: plot = client.replaceHTMLCodes(six.ensure_str(plot, errors='replace'))

            try: tagline = item['tagline']
            except: tagline = ''
            if not tagline: tagline = '0'
            else: tagline = client.replaceHTMLCodes(six.ensure_str(tagline, errors='replace'))

            if not self.lang == 'en':
                translations = item.get('translations', {})
                translations = translations.get('translations', [])
                trans_item = [x['data'] for x in translations if x.get('iso_639_1') == 'en'][0]

                en_title = trans_item.get('name', '')
                if en_title and not original_language == 'en': title = label = six.ensure_str(en_title)

                if plot == '0':
                    en_plot = trans_item.get('overview', '')
                    if en_plot: plot = client.replaceHTMLCodes(six.ensure_str(en_plot, errors='replace'))

                if tagline == '0':
                    en_tagline = trans_item.get('tagline', '')
                    if en_tagline: tagline = client.replaceHTMLCodes(six.ensure_str(en_tagline, errors='replace'))

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

            poster1 = self.list[i].get('poster', '0') or '0'

            poster_path = item.get('poster_path')
            if poster_path:
                poster2 = self.tm_img_link % ('500', poster_path)
                poster2 = six.ensure_str(poster2)
            else:
                poster2 = None

            fanart_path = item.get('backdrop_path')
            if fanart_path:
                fanart1 = self.tm_img_link % ('1280', fanart_path)
                fanart1 = six.ensure_str(fanart1)
            else:
                fanart1 = '0'

            # art = item.get('images')

            # try:
                # poster2 = art['posters']
                # poster2 = [x for x in poster2 if x.get('iso_639_1') == self.lang] + [x for x in poster2 if x.get('iso_639_1') == 'en'] + [x for x in poster2 if x.get('iso_639_1') not in [self.lang, 'en']]
                # poster2 = sorted(poster2, key=lambda x: x['width'])[0]
                # poster2 = poster2['file_path']
                # poster2 = self.tm_img_link % ('500', poster2)
                # poster2 = six.ensure_str(poster2)
            # except:
                # poster2 = '0'

            # try:
                # fanart = art['backdrops']
                # fanart = [x for x in fanart if x.get('iso_639_1') == self.lang] + [x for x in fanart if x.get('iso_639_1') == 'en'] + [x for x in fanart if x.get('iso_639_1') not in [self.lang, 'en']]
                # fanart = [x for x in fanart if x.get('width') == 1920] + [x for x in fanart if x.get('width') < 1920]
                # fanart = [(x['width'], x['file_path']) for x in fanart]
                # fanart = [(x[0], x[1]) if x[0] < 1280 else ('1280', x[1]) for x in fanart]
                # fanart = self.tm_img_link % fanart[0]
                # fanart = six.ensure_str(fanart)
            # except:
                # fanart = '0'

            poster3 = fanart2 = None
            banner = clearlogo = clearart = landscape = '0'
            if self.hq_artwork == 'true' and not tvdb == '0':# and not self.fanart_tv_user == '':

                artmeta = True
                try:
                    #if self.fanart_tv_user == '': raise Exception()
                    art = client.request(self.fanart_tv_art_link % tvdb, headers=self.fanart_tv_headers, timeout='10', error=True)
                    try: art = json.loads(art)
                    except: artmeta = False
                except:
                    artmeta = False

                if artmeta == False: pass

                try:
                    _poster3 = art['tvposter']
                    _poster3 = [x for x in _poster3 if x.get('lang') == self.lang][::-1] + [x for x in _poster3 if x.get('lang') == 'en'][::-1] + [x for x in _poster3 if x.get('lang') in ['00', '']][::-1]
                    _poster3 = _poster3[0]['url']
                    if _poster3: poster3 = six.ensure_str(_poster3)
                except:
                    pass

                try:
                    _fanart2 = art['showbackground']
                    _fanart2 = [x for x in _fanart2 if x.get('lang') == self.lang][::-1] + [x for x in _fanart2 if x.get('lang') == 'en'][::-1] + [x for x in _fanart2 if x.get('lang') in ['00', '']][::-1]
                    _fanart2 = _fanart2[0]['url']
                    if _fanart2: fanart2 = six.ensure_str(_fanart2)
                except:
                    pass

                try:
                    _banner = art['tvbanner']
                    _banner = [x for x in _banner if x.get('lang') == self.lang][::-1] + [x for x in _banner if x.get('lang') == 'en'][::-1] + [x for x in _banner if x.get('lang') in ['00', '']][::-1]
                    _banner = _banner[0]['url']
                    if _banner: banner = six.ensure_str(_banner)
                except:
                    pass

                try:
                    if 'hdtvlogo' in art: _clearlogo = art['hdtvlogo']
                    else: _clearlogo = art['clearlogo']
                    _clearlogo = [x for x in _clearlogo if x.get('lang') == self.lang][::-1] + [x for x in _clearlogo if x.get('lang') == 'en'][::-1] + [x for x in _clearlogo if x.get('lang') in ['00', '']][::-1]
                    _clearlogo = _clearlogo[0]['url']
                    if _clearlogo: clearlogo = six.ensure_str(_clearlogo)
                except:
                    pass

                try:
                    if 'hdclearart' in art: _clearart = art['hdclearart']
                    else: _clearart = art['clearart']
                    _clearart = [x for x in _clearart if x.get('lang') == self.lang][::-1] + [x for x in _clearart if x.get('lang') == 'en'][::-1] + [x for x in _clearart if x.get('lang') in ['00', '']][::-1]
                    _clearart = _clearart[0]['url']
                    if _clearart: clearart = six.ensure_str(_clearart)
                except:
                    pass

                try:
                    if 'tvthumb' in art: _landscape = art['tvthumb']
                    else: _landscape = art['showbackground']
                    _landscape = [x for x in _landscape if x.get('lang') == self.lang][::-1] + [x for x in _landscape if x.get('lang') == 'en'][::-1] + [x for x in _landscape if x.get('lang') in ['00', '']][::-1]
                    _landscape = _landscape[0]['url']
                    if _landscape: landscape = six.ensure_str(_landscape)
                except:
                    pass

            poster = poster3 or poster2 or poster1
            fanart = fanart2 or fanart1
            #log_utils.log('title: ' + title + ' - tvdb: ' + tvdb + ' - poster: ' + repr(poster))

            item = {'title': title, 'originaltitle': title, 'label': label, 'year': year, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart, 'banner': banner,
                    'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'mpaa': mpaa,
                    'castwiththumb': castwiththumb, 'cast': cast, 'plot': plot, 'status': status, 'tagline': tagline}
            item = dict((k,v) for k, v in six.iteritems(item) if not v == '0')
            #log_utils.log('superinfo_item: ' + str(item))
            self.list[i].update(item)

            #if artmeta == False: raise Exception()

            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'lang': self.lang, 'user': self.user, 'item': item}
            self.meta.append(meta)
        except:
            log_utils.log('superinfo_fail', 1)
            pass


    def tvshowDirectory(self, items):
        if items == None or len(items) == 0: control.idle() ; sys.exit()

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()

        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')

        traktCredentials = trakt.getTraktCredentialsInfo()

        try: isOld = False ; control.item().getArt('type')
        except: isOld = True

        indicators = playcount.getTVShowIndicators(refresh=True) if action == 'tvshows' else playcount.getTVShowIndicators() #fixme

        flatten = True if control.setting('flatten.tvshows') == 'true' else False

        watchedMenu = control.lang(32068) if trakt.getTraktIndicatorsInfo() == True else control.lang(32066)

        unwatchedMenu = control.lang(32069) if trakt.getTraktIndicatorsInfo() == True else control.lang(32067)

        queueMenu = control.lang(32065)

        traktManagerMenu = control.lang(32070)

        nextMenu = control.lang(32053)

        playRandom = control.lang(32535)

        addToLibrary = control.lang(32551)

        findSimilar = control.lang(32100)

        infoMenu = control.lang(32101)

        for i in items:
            try:
                label = i['label'] if 'label' in i and not i['label'] == '0' else i['title']
                status = i.get('status', '')
                try:
                    premiered = i['premiered']
                    if (premiered == '0' and status in ['Upcoming', 'In Production', 'Planned']) or (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))):
                        label = '[COLOR crimson]%s [I][Upcoming][/I][/COLOR]' % label
                except: pass

                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster

                systitle = sysname = urllib_parse.quote_plus(i['title'])
                sysimage = urllib_parse.quote_plus(poster)
                imdb, tvdb, tmdb, year = i.get('imdb', ''), i.get('tvdb', ''), i.get('tmdb', ''), i.get('year', '')

                meta = dict((k,v) for k, v in six.iteritems(i) if not (v == '0' or 'cast' in k))
                meta.update({'code': imdb, 'imdbnumber': imdb, 'imdb_id': imdb})
                meta.update({'tvdb_id': tvdb})
                meta.update({'tmdb_id': tmdb})
                meta.update({'mediatype': 'tvshow'})
                meta.update({'tvshowtitle': i['title']})
                meta.update({'trailer': '%s?action=trailer&name=%s' % (sysaddon, systitle)})
                if not 'duration' in i: meta.update({'duration': '60'})
                elif i['duration'] == '0': meta.update({'duration': '60'})
                try: meta.update({'duration': str(int(meta['duration']) * 60)})
                except: pass
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                except: pass

                try:
                    overlay = int(playcount.getTVShowOverlay(indicators, imdb, tmdb))
                    if overlay == 7: meta.update({'playcount': 1, 'overlay': 7})
                    else: meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass

                cm = []

                cm.append((findSimilar,
                           'ActivateWindow(10025,%s?action=tvshows&url=https://api.trakt.tv/shows/%s/related)' % (
                           sysaddon, imdb)))

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=season&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (
                          sysaddon, urllib_parse.quote_plus(systitle), urllib_parse.quote_plus(year), urllib_parse.quote_plus(imdb), urllib_parse.quote_plus(tmdb)))
                          )

                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                cm.append((watchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tmdb=%s&query=7)' % (sysaddon, systitle, imdb, tmdb)))

                cm.append((unwatchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tmdb=%s&query=6)' % (sysaddon, systitle, imdb, tmdb)))

                if traktCredentials == True:
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, sysname, tmdb)))

                if isOld == True:
                    cm.append((infoMenu, 'Action(Info)'))

                cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, systitle, year, imdb, tmdb)))

                try: item = control.item(label=label, offscreen=True)
                except: item = control.item(label=label)


                art = {}

                art.update({'icon': poster, 'thumb': poster, 'poster': poster, 'tvshow.poster': poster, 'season.poster': poster})

                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart

                if settingFanart == 'true':
                    art.update({'fanart': fanart})
                else:
                    art.update({'fanart': addonFanart})

                banner1 = i.get('banner', '')
                banner = banner1 or fanart or addonBanner
                art.update({'banner': banner})

                if 'clearlogo' in i and not i['clearlogo'] == '0':
                    art.update({'clearlogo': i['clearlogo']})

                if 'clearart' in i and not i['clearart'] == '0':
                    art.update({'clearart': i['clearart']})

                if 'landscape' in i and not i['landscape'] == '0':
                    landscape = i['landscape']
                else:
                    landscape = fanart
                art.update({'landscape': landscape})

                castwiththumb = i.get('castwiththumb', []) or []
                cast = i.get('cast', []) or []
                try: item.setCast(castwiththumb)
                except: meta.update({'cast': cast})
                item.setArt(art)
                item.addContextMenuItems(cm)
                item.setInfo(type='Video', infoLabels=control.metadataClean(meta))

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                # if flatten == True:
                    # url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&fanart=%s&duration=%s' % (sysaddon, systitle, year, imdb, tmdb, fanart, i['duration'])
                # else:
                    # url = '%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s' % (sysaddon, systitle, year, imdb, tmdb)
                url = '%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s' % (sysaddon, systitle, year, imdb, tmdb)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                log_utils.log('addir_fail', 1)
                pass

        try:
            url = items[0]['next']
            if url == '': raise Exception()

            icon = control.addonNext()
            url = '%s?action=tvshowPage&url=%s' % (sysaddon, urllib_parse.quote_plus(url))

            try: item = control.item(label=nextMenu, offscreen=True)
            except: item = control.item(label=nextMenu)

            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon, 'fanart': addonFanart})

            control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
        except:
            pass

        control.content(syshandle, 'tvshows')
        control.directory(syshandle, cacheToDisc=True)
        views.setView('tvshows', {'skin.estuary': 55, 'skin.confluence': 500})


    def addDirectory(self, items, queue=False):
        if items == None or len(items) == 0: control.idle() ; sys.exit()

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        addonFanart, addonThumb, artPath = control.addonFanart(), control.addonThumb(), control.artPath()

        queueMenu = control.lang(32065)

        playRandom = control.lang(32535)

        addToLibrary = control.lang(32551)

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

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=show&url=%s)' % (sysaddon, urllib_parse.quote_plus(i['url']))))

                if queue == True:
                    cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try: cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowsToLibrary&url=%s)' % (sysaddon, urllib_parse.quote_plus(i['context']))))
                except: pass

                try: item = control.item(label=name, offscreen=True)
                except: item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': addonFanart})

                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                pass

        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)
