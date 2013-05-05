# Author: Nic Wolfe <nic@wolfeden.ca>
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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import datetime

import sickbeard

from sickbeard import logger
from sickbeard import exceptions
from sickbeard import ui
from sickbeard.exceptions import ex

class ShowUpdater():

    def __init__(self):
        self.updateInterval = datetime.timedelta(hours=1)
        self.lastRun = None

    def run(self, force=False):

        doRun = False
        
        # If the update is forced or is the first run, do the full update
        if self.lastRun == None or force:
            doRun = True
            logger.log(u"Full update on all shows was forced or it is the first run")
        else:
            # Otherwise only do that once per day at the same hour of the last update.
            timedelta = datetime.datetime.today() - self.lastRun
            
            # if it's less than an interval after the update time then do an update (or if we're forcing it)
            if timedelta.total_seconds() - 24 * 60 * 60 >= 0:
                logger.log(u"Doing full update on all shows. Last run was: " + str(self.lastRun))
                doRun = True
            
        if doRun == False:
            return
            
        self.lastRun = datetime.datetime.today()
            
        piList = []

        for curShow in sickbeard.showList:

            try:

                if curShow.status != "Ended":
                    curQueueItem = sickbeard.showQueueScheduler.action.updateShow(curShow, True) #@UndefinedVariable
                else:
                    #TODO: maybe I should still update specials?
                    logger.log(u"Not updating episodes for show "+curShow.name+" because it's marked as ended.", logger.DEBUG)
                    curQueueItem = sickbeard.showQueueScheduler.action.refreshShow(curShow, True) #@UndefinedVariable

                piList.append(curQueueItem)

            except (exceptions.CantUpdateException, exceptions.CantRefreshException), e:
                logger.log(u"Automatic update failed: " + ex(e), logger.ERROR)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", piList))
