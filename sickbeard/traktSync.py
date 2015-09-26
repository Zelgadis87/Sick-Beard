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
from lib.dateutil import parser

import sickbeard
from sickbeard import logger
from sickbeard import db
from sickbeard import trakt
from sickbeard import search_queue

from common import WANTED, WAITING

class TraktSync:
    """
    A synchronizer for trakt.tv which keeps track of which episode has and hasn't been watched.
    """

    def __init__(self):
        self.amActive = False

    def _use_me(self):
        return sickbeard.USE_TRAKT and sickbeard.USE_TRAKT_SYNC

    def updateWatchedData(self):

        self.amActive = True

        method = "users/me/history/episodes"
        response = trakt.sendData(method);

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

        else:
            logger.log("Watched episodes synchronization failed.")

        self.updateNextEpisodeData();

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

        for show in showList:
            if show.stay_ahead > 0:
                sqlResults = myDB.select("SELECT season, episode, name FROM tv_episodes WHERE status = ? and episode_id IN (select ep.episode_id from tv_episodes ep left join trakt_data trakt on trakt.showid = ep.showid where ep.showid = ? AND ep.season > 0 AND ((trakt.next_season IS NULL) OR (trakt.next_season > -1 AND ((ep.season > trakt.next_season) OR (ep.season = trakt.next_season AND ep.episode >= trakt.next_episode)))) order by ep.season ASC, ep.episode ASC limit ?)", [WAITING, show.tvdbid, show.stay_ahead]);
                if len(sqlResults) > 0:
                    myDB.action("UPDATE tv_episodes set status = ? where status = ? and episode_id IN (select ep.episode_id from tv_episodes ep left join trakt_data trakt on trakt.showid = ep.showid where ep.showid = ? AND ep.season > 0 AND ((trakt.next_season IS NULL) OR (trakt.next_season > -1 AND ((ep.season > trakt.next_season) OR (ep.season = trakt.next_season AND ep.episode >= trakt.next_episode)))) order by ep.season ASC, ep.episode ASC limit ?)", [WANTED, WAITING, show.tvdbid, show.stay_ahead])

                    for row in sqlResults:
                        ep = show.getEpisode(int(row["season"]), int(row["episode"]))
                        logger.log(show.name + ": Episode " + ep.prettyName() + " queued for download due to StayAhead policies.")

                        queue_item = search_queue.ManualSearchQueueItem(ep)
                        sickbeard.searchQueueScheduler.action.add_item(queue_item) #@UndefinedVariable

        logger.log("Synchronization complete.")
        self.amActive = False

    def run(self):
        self.updateWatchedData()
