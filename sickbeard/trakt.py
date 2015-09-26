
import sickbeard;
from sickbeard import logger, ui

import time
import threading;
import urllib2;

try:
    import json;
except ImportError:
    from lib import simplejson as json;

class Trakt:

    def __init__(self):
        self._auth_lock = threading.Condition();
        self._auth_requesting = False;
        self._trakt_api_url = "https://api-v2launch.trakt.tv/";

    def _apiAccessToken(self):
        return sickbeard.TRAKT_API_ACCESS_TOKEN;

    def _apiRefreshToken(self):
        return sickbeard.TRAKT_API_REFRESH_TOKEN;

    def _apiTokenExpiration(self):
        return sickbeard.TRAKT_API_EXPIRATION_TOKEN;

    def _apiClientId(self):
        return '5cee6dc086ddb9afc27685fb33970fbe626efd79e2e5e9f6100c1d2c595d26c6'

    def _apiClientSecret(self):
        return '08dcfc97632db6346cb4ce669642dfc7e5ec4357f8a283cf080692ed3c49300d'

    def _waitOrRequestAuthentication(self):
        authenticationThreadOwner = False;
        if not self._auth_requesting:
            _auth_requesting = True;
            authenticationThreadOwner = True;

            thread = threading.Thread(None, self.authenticate, "TraktAuthorizer");
            thread.start();

        self._auth_lock.wait();

        if authenticationThreadOwner:
            _auth_requesting = False

    def authenticate(self, pin = None):
        """Invoked by a custom thread to acquire a valid trakt token, to use for
        all the following requests"""
        self._auth_lock.acquire();

        data = {};
        data["client_id"] = self._apiClientId();
        data["client_secret"] = self._apiClientSecret();
        data["redirect_uri"] = "urn:ietf:wg:oauth:2.0:oob";

        canAuthenticate = True;
        authenticationSuccesfull = False;
        if pin != None:
            data["grant_type"] = "authorization_code";
            data["code"] = pin;
        elif self._apiRefreshToken() != '':
            data["grant_type"] = "refresh_token";
            data["refresh_token"] = self._apiRefreshToken();
        else:
            canAuthenticate = False;

        if canAuthenticate:
            request = urllib2.Request("https://trakt.tv/oauth/token");
            request.add_header("content-type", "application/json");
            request.add_data(json.dumps(data));

            try:
                logger.log("trakt: Authenticating ...", logger.DEBUG)
                stream = urllib2.urlopen(request, timeout=120)

                ret = json.loads(stream.read());

                if not "error" in ret:
                    sickbeard.TRAKT_API_ACCESS_TOKEN = ret["access_token"];
                    sickbeard.TRAKT_API_REFRESH_TOKEN = ret["refresh_token"];
                    sickbeard.TRAKT_API_EXPIRATION_TOKEN = int(time.time()) + int(ret["expires_in"]);

                authenticationSuccesfull = True;
            except (IOError), e:
                ui.notifications.error("Trakt", "Failed to authenticate, please check your settings.")
                logger.log("trakt: Failed to authenticate (" + str(e.code) + "): " + e.reason, logger.ERROR)
                time.sleep(5)

        self._auth_lock.notify_all();
        self._auth_lock.release();

        if not canAuthenticate:
            ui.notifications.error("Trakt", "Failed to authenticate, please authorize this application in the settings.")
            raise Exception("Cannot authenticate to Trakt: No PIN code or RefreshToken available.");

        return authenticationSuccesfull

    def sendData(self, method, data = None):

        if self._apiAccessToken() == '':
            logger.log("trakt: Cannot make request without access token.");
            return None;

        if int(time.time()) > self._apiTokenExpiration():
            self._waitOrRequestAuthentication();

        request_url = self._trakt_api_url + method;
        request = urllib2.Request(request_url);
        request.add_header("Content-Type", "application/json");
        request.add_header("Trakt-Api-Version", 2);
        request.add_header("Trakt-Api-Key", self._apiClientId());
        request.add_header("Authorization", "Bearer " + self._apiAccessToken());

        encoded_data = "";
        if data:
            encoded_data = json.dumps(data);
            request.add_data(encoded_data);

        # request the URL from trakt and parse the result as json
        try:
            logger.log("trakt_sync: Calling method " + request_url + ", with data: " + encoded_data, logger.DEBUG)
            stream = urllib2.urlopen(request, timeout = 20)
            resp = json.loads(stream.read())

            if ("error" in resp):
                raise Exception(resp["error"])

        except (IOError), e:
            logger.log("trakt_sync: Failed calling method: " + e.message, logger.ERROR)
            return False

        return resp

_trakt_instance = Trakt();

def sendData(method, data = None):
    return _trakt_instance.sendData(method, data);

def authenticate(pin):
    return _trakt_instance.authenticate(pin);
