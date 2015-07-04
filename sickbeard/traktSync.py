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
import threading

from lib import dateutil
from lib.dateutil import parser

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard

from sickbeard import logger
from sickbeard import db
from sickbeard import ui

from common import DOWNLOADED, SNATCHED, SNATCHED_PROPER, ARCHIVED, IGNORED, UNAIRED, WANTED, SKIPPED, UNKNOWN, WAITING

class TraktSync:
    """
    A synchronizer for trakt.tv which keeps track of which episode has and hasn't been watched.
    """

    def __init__(self):
        self._auth_lock = threading.Condition();
        self._auth_token = None;
        self._auth_client = None;
        self._auth_requesting = False;
        self._trakt_api_url = "https://api.trakt.tv/";

    def _username(self):
        return sickbeard.TRAKT_USERNAME

    def _password(self):
        return sickbeard.TRAKT_PASSWORD

    def _api(self):
        return sickbeard.TRAKT_API

    def _use_me(self):
        return sickbeard.USE_TRAKT and sickbeard.USE_TRAKT_SYNC

    def requestToken(self):
        """Invoked by a custom thread to acquire a valid trakt token, to use for
        all the following requests"""
        self._auth_lock.acquire();

        data = {};
        data["login"] = self._username();
        data["password"] = self._password();

        request_url = self._trakt_api_url + "auth/login";
        request = urllib2.Request(request_url);
        request.add_header("content-type", "application/json");
        request.add_header("trakt-api-version", 2);
        request.add_header("trakt-api-key", self._api());
        request.add_header("trakt-user-login", self._username());

        request.add_data(json.dumps(data));

        try:
            logger.log("trakt_sync: Authenticating ...", logger.DEBUG)
            stream = urllib2.urlopen(request, timeout=120)

            self._auth_token = json.loads(stream.read())["token"];
        except (IOError), e:
            logger.log("trakt_sync: Failed to authenticate: " + e.message, logger.ERROR)
            time.sleep(5)

        self._auth_requesting = False
        self._auth_lock.notify_all();
        self._auth_lock.release();

    def _sendToTrakt(self, method, api = None, username = None, password = None, data = None, requires_auth = False):
        """
        A generic method for communicating with trakt. Uses the method along
        with the auth info to send the command.

        method: The URL to use at trakt, relative, no leading slash.
        api: The API string to provide to trakt
        username: The username to use when logging in
        password: The unencrypted password to use when logging in

        Returns: The data retrieved, or false if the request failed.
        """

        tryCount = 0

        self._auth_lock.acquire();
        while not self._auth_token and tryCount < 5:
            tryCount += 1;
            logger.log("trakt_sync: Waiting on auth token", logger.DEBUG)

            if not self._auth_requesting:
                self._auth_requesting = True;
                thread = threading.Thread(None, self.requestToken, "TraktAuthorizer");
                thread.start();

            self._auth_lock.wait();
        self._auth_lock.release();

        if tryCount >= 5:
            ui.notifications.error("Trakt", "Failed to authenticate, please check your settings.")
            return False;

        logger.log("trakt_sync: Call method " + method, logger.DEBUG)

        request_url = self._trakt_api_url + method;
        request = urllib2.Request(request_url);
        request.add_header("content-type", "application/json");
        request.add_header("trakt-api-version", 2);
        request.add_header("trakt-api-key", self._api());
        request.add_header("trakt-user-token", self._auth_token);
        request.add_header("trakt-user-login", self._username());

        encoded_data = "";
        if data:
            encoded_data = json.dumps(data);
            request.add_data(encoded_data);

        # request the URL from trakt and parse the result as json
        try:
            logger.log("trakt_sync: Calling method http://api.trakt.tv/" + method + ", with data" + encoded_data, logger.DEBUG)
            stream = urllib2.urlopen(request, timeout = 60)
            resp = json.loads(stream.read())

            if ("error" in resp):
                raise Exception(resp["error"])

        except (IOError), e:
            logger.log("trakt_sync: Failed calling method: " + e.message, logger.ERROR)
            return False

        return resp

    def updateWatchedData(self):
        method = "users/" + self._username() + "/history/episodes"
        response = self._sendToTrakt(method)

        if response != False:
            changes = dict();
            myDB = db.DBConnection()

            for data in response:

                show_name = data["show"]["title"]
                show_id = data["show"]["ids"]["tvdb"]
                season = data["episode"]["season"]
                episode = data["episode"]["number"]
                watched = time.mktime(parser.parse(data["watched_at"]).timetuple())

                cursor = myDB.action("UPDATE tv_episodes SET last_watched=? WHERE showid=? AND season=? AND episode=? AND (last_watched IS NULL OR last_watched < ?)", [watched, show_id, season, episode, watched])
                if cursor.rowcount > 0:
                    changes[show_name] = changes.get(show_name, 0) + 1
                    logger.log("Updated " + show_name + ", episode " + str(season) + "x" + str(episode) + " watched @ " + str(watched))

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

            self.updateNextEpisodeData();
        else:
            logger.log("Watched episodes synchronization failed.")

    def updateNextEpisodeData(self):

        myDB = db.DBConnection()
        myDB.action("DELETE FROM trakt_data;")

        update_datetime = int(time.time())
        showList = list(sickbeard.showList)

        for show in showList:
            sqlResults = myDB.select("SELECT season, episode FROM v_episodes_to_watch where showid = ? order by season asc, episode asc limit 1", [show.tvdbid]);
            if len(sqlResults) == 1:
                nextSeason = sqlResults[0]["season"];
                nextEpisode = sqlResults[0]["episode"];
            else:
                nextSeason = -1;
                nextEpisode = -1;

            myDB.action("INSERT INTO trakt_data(showid, next_season, next_episode, last_updated) VALUES(?, ?, ?, ?)", [show.tvdbid, nextSeason, nextEpisode, update_datetime]);

        logger.log("Next episodes synchronization complete.")
        self.updateEpisodesToAutoDownload()

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

        logger.log("Synchronization complete.")

    def run(self):
        self.updateWatchedData()
