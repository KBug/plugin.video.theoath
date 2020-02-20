# -*- coding: utf-8 -*-


##-- Fen add-on's debrid cache check module adjusted for TheOath/Exodus code base - all credits to Tikipeter --##
##--                                       Please retain this credit                                         --##


import xbmc, xbmcgui
import os
import json
import time
import datetime
import requests
try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database
from threading import Thread
from resources.lib.modules import control

__token__ = control.addon('script.module.resolveurl').getSetting('RealDebridResolver_token')
__client_id__ = control.addon('script.module.resolveurl').getSetting('RealDebridResolver_client_id')
__client_secret__ = control.addon('script.module.resolveurl').getSetting('RealDebridResolver_client_secret')
__refresh__ = control.addon('script.module.resolveurl').getSetting('RealDebridResolver_refresh')
__rest_base_url__ = 'https://api.real-debrid.com/rest/1.0/'
__auth_url__ = 'https://api.real-debrid.com/oauth/v2/'

progressDialog = control.progressDialogBG

def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]

def to_utf8(obj):
    try:
        import copy
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8', 'ignore')
        elif isinstance(obj, dict):
            obj = copy.deepcopy(obj)
            for key, val in obj.items():
                obj[key] = to_utf8(val)
        elif obj is not None and hasattr(obj, "__iter__"):
            obj = obj.__class__([to_utf8(x) for x in obj])
        else: pass
    except: pass
    return obj

def _get(url):
    original_url = url
    url = __rest_base_url__ + url
    if '?' not in url:
        url += "?auth_token=%s" % __token__
    else:
        url += "&auth_token=%s" % __token__
    response = requests.get(url).text
    if 'bad_token' in response or 'Bad Request' in response:
        refreshToken()
        response = _get(original_url)
    try: return to_utf8(json.loads(response))
    except: return to_utf8(response)

def refreshToken():
    data = {'client_id': __client_id__,
            'client_secret': __client_secret__,
            'code': __refresh__,
            'grant_type': 'http://oauth.net/grant_type/device/1.0'}
    url = __auth_url__ + 'token'
    response = requests.post(url, data=data)
    response = json.loads(response.text)
    if 'access_token' in response: _token = response['access_token']
    if 'refresh_token' in response: _refresh = response['refresh_token']
    control.addon('script.module.resolveurl').setSetting('RealDebridResolver_token', _token)
    control.addon('script.module.resolveurl').setSetting('RealDebridResolver_refresh', _refresh)

def check_cache(hashes):
    hash_string = '/'.join(hashes)
    url = 'torrents/instantAvailability/%s' % hash_string
    response = _get(url)
    return response

class DebridCheck:
    def __init__(self):
        self.db_cache = DebridCache()
        self.db_cache.check_database()
        self.cached_hashes = []
        self.main_threads = []
        self.rd_cached_hashes = []
        self.rd_hashes_unchecked = []
        self.rd_query_threads = []
        self.rd_process_results = []
        self.starting_debrids = []
        self.starting_debrids_display = []

    def run(self, hash_list):
        control.sleep(500)
        self.hash_list = hash_list
        self._query_local_cache(self.hash_list)
        self.rd_cached_hashes = [str(i[0]) for i in self.cached_hashes if str(i[1]) == 'rd' and str(i[2]) == 'True']
        self.rd_hashes_unchecked = [i for i in self.hash_list if not any([h for h in self.cached_hashes if str(h[0]) == i and str(h[1]) =='rd'])]
        if self.rd_hashes_unchecked: self.starting_debrids.append(('Real-Debrid', self.RD_cache_checker))
        if self.starting_debrids:
            for i in range(len(self.starting_debrids)):
                self.main_threads.append(Thread(target=self.starting_debrids[i][1]))
                self.starting_debrids_display.append((self.main_threads[i].getName(), self.starting_debrids[i][0]))
            [i.start() for i in self.main_threads]
            [i.join() for i in self.main_threads]
            self.debrid_check_dialog()
        control.sleep(500)
        return self.rd_cached_hashes

    def debrid_check_dialog(self):
        timeout = 20
        progressDialog.create(control.addonInfo('name'), 'Checking debrid-cache, please wait..')
        progressDialog.update(0)
        start_time = time.time()
        for i in range(0, 200):
            try:
                if xbmc.abortRequested == True: return sys.exit()
                try:
                    if progressDialog.iscanceled():
                        break
                except Exception:
                    pass
                alive_threads = [x.getName() for x in self.main_threads if x.is_alive() is True]
                remaining_debrids = [x[1] for x in self.starting_debrids_display if x[0] in alive_threads]
                current_time = time.time()
                current_progress = current_time - start_time
                try:
                    head = 'Checking Debrid Providers'
                    msg = 'Remaining Debrid Checks: %s' % ', '.join(remaining_debrids).upper()
                    percent = int((current_progress/float(timeout))*100)
                    progressDialog.update(percent, head, msg)
                except: pass
                time.sleep(0.2)
                if len(alive_threads) == 0: break
            except Exception:
                pass
        try:
            progressDialog.close()
        except Exception:
            pass
        control.sleep(200)

    def RD_cache_checker(self):
        hash_chunk_list = list(chunks(self.rd_hashes_unchecked, 100))
        for item in hash_chunk_list: self.rd_query_threads.append(Thread(target=self._rd_lookup, args=(item,)))
        [i.start() for i in self.rd_query_threads]
        [i.join() for i in self.rd_query_threads]
        self._add_to_local_cache(self.rd_process_results, 'rd')

    def _rd_lookup(self, chunk):
        try:
            rd_cache_get = check_cache(chunk)
            for h in chunk:
                cached = 'False'
                if h in rd_cache_get:
                    info = rd_cache_get[h]
                    if isinstance(info, dict) and len(info.get('rd')) > 0:
                        self.rd_cached_hashes.append(h)
                        cached = 'True'
                self.rd_process_results.append((h, cached))
        except: pass

    def _query_local_cache(self, _hash):
        cached = self.db_cache.get_all(_hash)
        if cached:
            self.cached_hashes = cached

    def _add_to_local_cache(self, _hash, debrid):
        self.db_cache.set_many(_hash, debrid)

class DebridCache:
    def __init__(self):
        self.dbfile = control.dbFile

    def get_all(self, hash_list):
        result = None
        try:
            current_time = self._get_timestamp(datetime.datetime.now())
            dbcon = database.connect(self.dbfile, timeout=40.0)
            dbcur = dbcon.cursor()
            dbcur.execute('SELECT * FROM debrid_data WHERE hash in ({0})'.format(', '.join('?' for _ in hash_list)), hash_list)
            cache_data = dbcur.fetchall()
            if cache_data:
                if cache_data[0][3] > current_time:
                    result = cache_data
                else:
                    self.remove_many(cache_data)
        except: pass
        return result

    def remove_many(self, old_cached_data):
        try:
            old_cached_data = [(str(i[0]),) for i in old_cached_data]
            dbcon = database.connect(self.dbfile, timeout=40.0)
            dbcur = dbcon.cursor()
            dbcur.executemany("DELETE FROM debrid_data WHERE hash=?", old_cached_data)
            dbcon.commit()
        except: pass

    def set_many(self, hash_list, debrid, expiration=datetime.timedelta(hours=1)):
        try:
            expires = self._get_timestamp(datetime.datetime.now() + expiration)
            insert_list = [(i[0], debrid, i[1], expires) for i in hash_list]
            dbcon = database.connect(self.dbfile, timeout=40.0)
            dbcur = dbcon.cursor()
            dbcur.executemany("INSERT INTO debrid_data VALUES (?, ?, ?, ?)", insert_list)
            dbcon.commit()
        except: pass

    def check_database(self):
        if not os.path.exists(control.dataPath):
            control.makeFile(control.dataPath)
        dbcon = database.connect(self.dbfile)
        dbcon.execute("""CREATE TABLE IF NOT EXISTS debrid_data
                      (hash text not null, debrid text not null, cached text, expires integer, unique (hash, debrid))
                        """)
        dbcon.close()

    def clear_database(self):
        try:
            dbcon = database.connect(self.dbfile)
            dbcur = dbcon.cursor()
            dbcur.execute("DELETE FROM debrid_data")
            dbcur.execute("VACUUM")
            dbcon.commit()
            dbcon.close()
            return 'success'
        except: return 'failure'

    def _get_timestamp(self, date_time):
        return int(time.mktime(date_time.timetuple()))






