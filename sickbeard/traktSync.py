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
from common import DOWNLOADED, SNATCHED, SNATCHED_PROPER, ARCHIVED, IGNORED, UNAIRED, WANTED, SKIPPED, UNKNOWN, WAITING

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

    def updateNextEpisodeData(self):
        update_datetime = int(time.time())

        method = "user/progress/watched.json/%API%/" + self._username() + "/"
        response = self._sendToTrakt(method, None, None, None)

        if response != False:
            myDB = db.DBConnection()

            nextSeason = 1
            nextEpisode = 1

            myDB.action("DELETE FROM trakt_data;")
            for data in response:
                show_id = data["show"]["tvdb_id"]
                if data["next_episode"] == False:
                    # the user has completed this serie.
                    nextSeason = -1
                    nextEpisode = -1
                else:
                    nextSeason = data["next_episode"]["season"]
                    nextEpisode = data["next_episode"]["number"]

                myDB.action("INSERT OR REPLACE INTO trakt_data(showid, next_season, next_episode, last_updated) VALUES(?, ?, ?, ?)", [show_id, nextSeason, nextEpisode, update_datetime])

                logger.log("Show " + str(show_id) + " updated. NextEpisode: " + ("COMPLETE" if nextSeason == False else str(nextSeason) + "x" + str(nextEpisode)), logger.DEBUG)

            logger.log("Next episodes synchronization complete.")
        else:
            logger.log("Next episodes synchronization failed.")

    def updateWatchedData(self):
        method = "user/watched.json/%API%/" + self._username() + "/"
        response = self._sendToTrakt(method, None, None, None)

        if response != False:
            changes = dict();
            myDB = db.DBConnection()

            for data in response:

                if data["type"] == "episode":
                    # We are only interested in tv episodes.
                    show_name = data["show"]["title"]
                    show_id = data["show"]["tvdb_id"]
                    season = data["episode"]["season"]
                    episode = data["episode"]["number"]
                    watched = data["watched"]

                    cursor = myDB.action("UPDATE tv_episodes SET last_watched=? WHERE showid=? AND season=? AND episode=? AND (last_watched IS NULL OR last_watched < ?)", [watched, show_id, season, episode, watched])
                    if cursor.rowcount > 0:
                        changes[show_name] = changes.get(show_name, 0) + 1

            message = "Watched episodes synchronization complete: ";
            if (len(changes) == 0):
                message += "No changes detected."
            else:
                message += "Marked as watched "
                first = True;
                for show_name in changes:
                    if (first):
                        message += ", "
                        first = False;
                    message += str(changes[show_name]) + " episodes of " + show_name + ""

            logger.log(message)
        else:
            logger.log("Watched episodes synchronization failed.")

    def updateEpisodesToAutoDownload(self):
        myDB = db.DBConnection()
        showList = list(sickbeard.showList)
        updatedShows = []

        for show in showList:
            if show.stay_ahead > 0:
                cursor = myDB.action("UPDATE tv_episodes set status = ? where status = ? and episode_id IN (select ep.episode_id from tv_episodes ep left join trakt_data trakt on trakt.showid = ep.showid where ep.showid = ? AND ep.season > 0 AND ((trakt.next_season IS NULL) OR (trakt.next_season > -1 AND ((ep.season > trakt.next_season) OR (ep.season = trakt.next_season AND ep.episode >= trakt.next_episode)))) order by ep.season ASC, ep.episode ASC limit ?)", [WANTED, WAITING, show.tvdbid, show.stay_ahead])
                if cursor.rowcount > 0:
                    updatedShows.append(show)
                    logger.log(str(cursor.rowcount) + " episodes of " + show.name + " queued for download.")

        if updatedShows:
            sickbeard.backlogSearchScheduler.action.searchBacklog(updatedShows)

    def run(self):
        self.updateNextEpisodeData()
        self.updateWatchedData()
        self.updateEpisodesToAutoDownload()
        logger.log("Synchronization complete.")