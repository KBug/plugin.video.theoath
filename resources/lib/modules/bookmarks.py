# -*- coding: utf-8 -*-

"""
    TheOath Add-on

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


import hashlib, traceback

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

from resources.lib.modules import control
from resources.lib.modules import playcount
from resources.lib.modules import trakt
from resources.lib.modules import log_utils

class Bookmarks:
    def get(self, name, season, episode, imdb, year='0'):
        offset = '0'

        if control.setting('rersume.source') == '1' and trakt.getTraktCredentialsInfo() == True:
            try:
                self.offset = '0'
                if not episode is None:

                    # Looking for a Episode progress
                    traktInfo = trakt.getTraktAsJson('https://api.trakt.tv/sync/playback/episodes?extended=full')
                    for i in traktInfo:
                        if imdb == i['show']['ids']['imdb']:
                            # Checking Episode Number
                            if int(season) == i['episode']['season'] and int(episode) == i['episode']['number']:
                                seekable = 1 < i['progress'] < 92
                                if seekable:
                                    # Calculating Offset to seconds
                                    self.offset = (float(i['progress'] / 100) * int(i['episode']['runtime']) * 60)
                                else:
                                    self.offset = '0'
                else:

                    # Looking for a Movie Progress
                    traktInfo = trakt.getTraktAsJson('https://api.trakt.tv/sync/playback/movies?extended=full')
                    for i in traktInfo:
                        if imdb == i['movie']['ids']['imdb']:
                            seekable = 1 < i['progress'] < 92
                            if seekable:
                                # Calculating Offset to seconds
                                self.offset = (float(i['progress'] / 100) * int(i['movie']['runtime']) * 60)
                            else:
                                self.offset = '0'

                return self.offset

            except:
                return offset

        else:
            try:

                idFile = hashlib.md5()
                for i in name: idFile.update(i.encode('utf-8'))
                for i in year: idFile.update(i.encode('utf-8'))
                idFile = idFile.hexdigest()

                dbcon = database.connect(control.bookmarksFile)
                dbcur = dbcon.cursor()
                dbcur.execute("SELECT * FROM bookmarks WHERE idFile = '%s'" % idFile)
                match = dbcur.fetchone()
                if match:
                    self.offset = str(match[1])
                    return self.offset
                    # if self.offset == '0':
                        # return offset
                        #raise Exception()
                else:
                    return offset
                dbcon.commit()
            except:
                failure = traceback.format_exc()
                log_utils.log('bookmarks_get: ' + str(failure))
                return offset


    def reset(self, current_time, total_time, type, imdb, season, episode, _name, _year='0'):
        try:
            playcount = 0
            overlay = 6
            timeInSeconds = str(current_time)
            ok = int(current_time) > 120 and (current_time / total_time) < .92
            watched = (current_time / total_time) >= .92

            idFile = hashlib.md5()
            for i in _name: idFile.update(i.encode('utf-8'))
            for i in _year: idFile.update(i.encode('utf-8'))
            idFile = idFile.hexdigest()

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.bookmarksFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS bookmarks (""idFile TEXT, ""timeInSeconds TEXT, ""type TEXT, ""imdb TEXT, ""season TEXT, ""episode TEXT, ""playcount INTEGER, ""overlay INTEGER, ""UNIQUE(idFile)"");")
            dbcur.execute("SELECT * FROM bookmarks WHERE idFile = '%s'" % idFile)
            match = dbcur.fetchone()
            if match:
                if ok:
                    dbcur.execute("UPDATE bookmarks SET timeInSeconds = ? WHERE idFile = ?", (timeInSeconds, idFile))
                elif watched:
                    playcount = match[6] + 1
                    overlay = 7
                    dbcur.execute("UPDATE bookmarks SET timeInSeconds = ?, playcount = ?, overlay = ? WHERE idFile = ?", ('0', playcount, overlay, idFile))
            else:
                if ok:
                    dbcur.execute("INSERT INTO bookmarks Values (?, ?, ?, ?, ?, ?, ?, ?)", (idFile, timeInSeconds, type, imdb, season, episode, playcount, overlay))
                elif watched:
                    playcount = 1
                    overlay = 7
                    dbcur.execute("INSERT INTO bookmarks Values (?, ?, ?, ?, ?, ?, ?, ?)", (idFile, '0', type, imdb, season, episode, playcount, overlay))
            dbcon.commit()
        except:
            failure = traceback.format_exc()
            log_utils.log('bookmarks_reset: ' + str(failure))
            pass


    def set_scrobble(self, current_time, total_time, _content, _imdb='', _tvdb='', _season='', _episode=''):
        try:
            percent = float((current_time / total_time)) * 100
            if int(current_time) > 120 and percent < 92:
                trakt.scrobbleMovie(_imdb, percent, action='pause') if _content == 'movie' else trakt.scrobbleEpisode(_imdb, _season, _episode, percent, action='pause')
                if control.setting('trakt.scrobble.notify') == 'true':
                    control.infoDialog('Trakt: Scrobble Paused')
            elif percent >= 92:
                trakt.scrobbleMovie(_imdb, percent, action='stop') if _content == 'movie' else trakt.scrobbleEpisode(_imdb, _season, _episode, percent, action='stop')
                if control.setting('trakt.scrobble.notify') == 'true':
                    control.infoDialog('Trakt: Scrobbled')
        except:
            failure = traceback.format_exc()
            log_utils.log('Scrobble - Exception: ' + str(failure))
            control.infoDialog('Scrobble Failed')

