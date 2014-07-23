# Author: Dieter Blomme <dieterblomme@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.


import time
import urllib2

from hashlib import sha1

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard

from sickbeard import logger
from sickbeard import db

class TraktSync:
    """
    A synchronizer for trakt.tv which keeps track of which episode has and hasn't been watched.
    """

    def _username(self):
        return sickbeard.TRAKT_USERNAME

    def _password(self):
        return sickbeard.TRAKT_PASSWORD

    def _api(self):
        return sickbeard.TRAKT_API

    def _use_me(self):
        return sickbeard.USE_TRAKT and sickbeard.USE_TRAKT_SYNC

    def _sendToTrakt(self, method, api, username, password, data = {}):
        """
        A generic method for communicating with trakt. Uses the method along
        with the auth info to send the command.

        method: The URL to use at trakt, relative, no leading slash.
        api: The API string to provide to trakt
        username: The username to use when logging in
        password: The unencrypted password to use when logging in

        Returns: The data retrieved, or false if the request failed.
        """
        logger.log("trakt_sync: Call method " + method, logger.DEBUG)

        # if the API isn't given then use the config API
        if not api:
            api = self._api()

        # if the username isn't given then use the config username
        if not username:
            username = self._username()

        # if the password isn't given then use the config password
        if not password:
            password = self._password()
        password = sha1(password).hexdigest()

        # replace the API string with what we found
        method = method.replace("%API%", api)

        data["username"] = username
        data["password"] = password

        # take the URL params and make a json object out of them
        encoded_data = json.dumps(data);

        # request the URL from trakt and parse the result as json
        try:
            logger.log("trakt_sync: Calling method http://api.trakt.tv/" + method + ", with data" + encoded_data, logger.DEBUG)
            stream = urllib2.urlopen("http://api.trakt.tv/" + method, encoded_data)
            resp = stream.read()

            resp = json.loads(resp)

            if ("error" in resp):
                raise Exception(resp["error"])

        except (IOError):
            logger.log("trakt_sync: Failed calling method", logger.ERROR)
            return False

        return resp

    def _updateData(self, show_id):
        update_datetime = int(time.time())

        method = "user/progress/watched.json/%API%/" + self._username() + "/" + str(show_id)
        response = self._sendToTrakt(method, None, None, None)

        if response != False:
            myDB = db.DBConnection()

            completed = False
            nextSeason = 1
            nextEpisode = 1
            if len(response) > 0:
                data = response[0]
                if data["next_episode"] == False:
                    # the user has completed this serie.
                   completed = True
                else:
                    nextSeason = data["next_episode"]["season"]
                    nextEpisode = data["next_episode"]["number"]
                    completed = False

            if completed:
                myDB.action("INSERT OR REPLACE INTO trakt_data(showid, last_watched_season, last_watched_episode, last_updated) VALUES(?, (SELECT MAX(season) FROM tv_episodes WHERE showid = ?), (SELECT MAX(episode) FROM tv_episodes WHERE showid = ?), ?)", [show_id, show_id, show_id, update_datetime])
            else:
                myDB.action("INSERT OR REPLACE INTO trakt_data(showid, last_watched_season, last_watched_episode, last_updated) VALUES(?, ?, ?, ?)", [show_id, nextSeason, nextEpisode, update_datetime])

            logger.log("trakt_sync: Show " + str(show_id) + " updated. NextEpisode: " + ("COMPLETE" if completed else str(nextSeason) + "x" + str(nextEpisode)))

    def refreshShowStatus(self, show_obj):
        self._updateData(show_obj.tvdb_id)

    def refreshLibraryStatus(self):
        myDB = db.DBConnection()
        sql_result = myDB.select("SELECT tv_shows.tvdb_id, trakt_data.last_updated FROM tv_shows LEFT JOIN trakt_data ON trakt_data.showid = tv_shows.tvdb_id WHERE trakt_data.last_updated IS NULL OR trakt_data.last_watched_season < (SELECT MAX(season) FROM tv_episodes WHERE showid = tv_shows.tvdb_id) OR trakt_data.last_watched_episode < (SELECT MAX(season) FROM tv_episodes WHERE showid = tv_shows.tvdb_id) GROUP BY tv_shows.show_id ORDER BY trakt_data.last_updated ASC LIMIT 10")

        count = 0
        for cur_result in sql_result:
            count += 1
            self._updateData(cur_result['tvdb_id'])

        if count == 0:
            logger.log("trakt_sync: No show to update.")

    def run(self):
        self.refreshLibraryStatus()