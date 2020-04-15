import logging
from threading import Thread

from distribution.node_client import NodeClient

_logger = logging.getLogger(__name__)

HEARTBEAT_FREQUENCY_SEC = 3


class Heartbeat(Thread):
    def __init__(self, event, kill_clients_on_disconnect, client_restart_attempts=0):
        Thread.__init__(self)
        self.kill_clients_on_disconnect = kill_clients_on_disconnect
        self.client_restart_attempts = client_restart_attempts # TODO intentionally made this different name than yml file. is that good/bad?
        self.stopped = event
        self.success = None
        self.node_client = NodeClient(None)

    def run(self):
        while not self.stopped.wait(HEARTBEAT_FREQUENCY_SEC):
            client_statuses = self.node_client.get_client_statuses()
            dead_clients = [c for c in client_statuses if not c['alive'] or not c['busy']]
            alive_clients = [c for c in client_statuses if c['alive'] and c['busy']]

            # TODO there should be some number of times to restart client (using flag)

            if dead_clients: 
                if self.kill_clients_on_disconnect:
                    _logger.critical('kill_clients_on_disconnect is registering as True')
                    printable_names = '.'.join([c['address'] for c in dead_clients])
                    _logger.critical('Heartbeat: One or more clients ({}) are not alive anymore; '
                                    'exiting others as well.'.format(printable_names))

                    self.node_client.stop_running_experiments(dead_clients)
                    self.success = False
                    return
                elif self.client_restart_attempts > 0:
                    _logger.critical('dead clients are {} will try to restart client'.format(dead_clients))
                    return 
            elif all(c['finished'] for c in alive_clients):
                _logger.info('Heartbeat: All clients finished their experiments.')
                self.success = True
                return
