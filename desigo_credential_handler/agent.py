"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import http
import logging
import sys
import traceback

from datetime import datetime, timedelta

import gevent
import grequests

from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "1.0.0"


def desigo_credential_handler(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: DesigoCredentialHandler
    :rtype: DesigoCredentialHandler
    """

    return DesigoCredentialHandler(**kwargs)


class DesigoCredentialHandler(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, **kwargs):
        super(DesigoCredentialHandler, self).__init__(**kwargs)

        self.api_username = None
        self.api_password = None
        self.servers = {}
        self.auth_token = None
        self.token_lock = gevent.lock.BoundedSemaphore()
        self.last_returned_token = datetime.now() - timedelta(minutes=15)

        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus. If a configuration exists at startup
        this will be called before onstart.

        Is called every time the configuration in the store changes.
        """

        _log.debug("Configuring Agent")

        if config_name == "config":
            if not contents.get("servers"):
                _log.warning("No servers configured")
                return
            for server in contents["servers"]:
                try:
                    self.servers[server["url"]] = server
                except KeyError:
                    _log.warning(f"Invalid server configuration {server}")
                    continue
        else:
            _log.warning(f"Invalid configuration name {config_name}")
            return
        
    @RPC.export
    def get_token(self, url, **kwargs):
        """
        Retrieve new token from server
        """
        with self.token_lock:
            if datetime.now() - timedelta(minutes=15) < self.last_returned_token:
                _log.debug(f"returning cached token: ...{self.auth_token[-4:]}")
                return self.auth_token

            try:
                data = {
                    "grant_type": "password",
                    "username": self.servers[url]["user"],
                    "password": self.servers[url]["password"],
                }
            except KeyError:
                _log.error(f"Invalid server url {url}")
                _log.debug(f"{self.servers=}")
                return None
            req = grequests.post(f"{url}/token", data=data, verify=False, timeout=300)
            (result,) = grequests.map(
                (req,), exception_handler=self._grequests_exception_handler
            )

            if result is None and not kwargs.get("retry"):
                _log.error("could not get token, trying once more in 5 seconds")
                gevent.sleep(5)
                self.get_token(url, retry=True)
                return None
            elif result is None and kwargs.get("retry"):
                _log.error("could not get token, giving up")
                return None
            try:
                _log.info(f"acquired new access_token: ...{result.json()['access_token'][-4:]}")
                self.auth_token = result.json()["access_token"]
            except KeyError:
                _log.debug(f"could not get access_token from JSON: {result.json()=}")
                return None
            self.last_returned_token = datetime.now()
            return self.auth_token

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        # Example publish to pubsub
        self.vip.pubsub.publish('pubsub', "some/random/topic", message="HI!")

        # Example RPC call
        # self.vip.rpc.call("some_agent", "some_method", arg1, arg2)
        pass

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        pass

    def _grequests_exception_handler(self, request, exception):
        """
        Log exceptions from grequests
        """
        trace = traceback.format_exc()
        _log.error(f"grequests error: {exception} with {request}: {trace=}")


def main():
    """Main method called to start the agent."""
    utils.vip_main(desigo_credential_handler, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
