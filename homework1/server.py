import os
import sys
import time
import socket
import select
try:
    import homework1.base as base
except Exception:
    import base


HELP_MESSAGE = 'Usage: <script_name> <port> <protocol> <messages_size> <mechanism>.\n' \
               '<port> - A port number\n' \
               '<protocol> - A string equal to "TCP" or "UDP"\n' \
               '<messages_size> - An integer representing the size of the messages sent\n' \
               '<mechanism> - A equal to "STREAMING" or "STOP-AND-WAIT"\n'


class Server(base.BaseWorker):
    def __init__(self, port: int, protocol: str, messages_size: int, mechanism: str):
        super().__init__()

        self.port = port
        self.protocol = protocol
        self.mechanism = mechanism
        self.messages_size = messages_size

        self.bytes_read = 0
        self.messages_received = 0

        self.connections = dict()

    def initialize(self):
        super().initialize()

        if self.protocol == self.PROTOCOLS['TCP']:
            self.connection = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM
            )
            self.connection.bind(('0.0.0.0', self.port))
            self.connection.listen(5)
            self.logger.info('Using TCP.')
        elif self.protocol == self.PROTOCOLS['UDP']:
            self.connection = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_DGRAM
            )
            self.connection.bind(('0.0.0.0', self.port))
            self.logger.info('Using UDP.')

        self.sockets_to_read = [self.connection]
        self.sockets_to_write = []
        self.sockets_with_exceptional_condition = []

    def process_socket(self, socket: socket.socket):
        message, address = None, None

        if self.protocol == self.PROTOCOLS['TCP']:
            if socket == self.connection:
                new_connection, address = self.connection.accept()
                self.connections[new_connection] = {
                    'address': address,
                    'messages_received': 0,
                    'bytes_received': 0
                }
                self.sockets_to_read.append(new_connection)

                self.logger.info('Received new connection from address {}.'.format(address))
            else:
                message = socket.recv(self.messages_size)
                if message:
                    if message == self.STOP_MESSAGE:
                        self.logger.info('Received stop message.')
                        self.dump_stats(socket)
                        self.sockets_to_read.remove(socket)
                        self.connections.pop(socket)
                    else:
                        self.logger.info('Received a message.')
                        self.connections[socket]['bytes_received'] = self.connections[socket]['bytes_received'] + len(message)
                        self.connections[socket]['messages_received'] = self.connections[socket]['messages_received'] + 1

                    if self.mechanism == self.MECHANISMS['STOP-AND-WAIT'] or message == self.STOP_MESSAGE:
                        socket.send(self.ACKNOWLEDGEMENT_MESSAGE)
                        self.logger.info('Sent confirmation')

                    if message == self.STOP_MESSAGE:
                        socket.close()
        elif self.protocol == self.PROTOCOLS['UDP']:
            try:
                message, address = socket.recvfrom(self.messages_size)
                self.logger.info('Received a message from {}.'.format(address))
            except Exception as exc:
                self.logger.info('No message received: {}'.format(exc))

            if message:
                if self.mechanism == self.MECHANISMS['STOP-AND-WAIT']:
                    self.connection.sendto(
                        self.ACKNOWLEDGEMENT_MESSAGE,
                        address
                    )
                    self.logger.info('Sent confirmation to {}.'.format(address))

                if address not in self.connections:
                    self.connections[address] = {
                        'address': address,
                        'bytes_received': 0,
                        'messages_received': 0
                    }

                if message == self.STOP_MESSAGE:
                    self.logger.info('Received stop message.')
                    self.dump_stats(address)
                    self.connections.pop(address)

                    self.connection.sendto(
                        self.ACKNOWLEDGEMENT_MESSAGE,
                        address
                    )
                else:
                    self.connections[address]['bytes_received'] = self.connections[address]['bytes_received'] \
                                                                  + len(message)
                    self.connections[address]['messages_received'] = self.connections[address]['messages_received'] + 1
            else:
                self.logger.info('No message received. :(')

        return message

    def run(self):
        self.logger.info('Initializing')
        try:
            self.initialize()
        except Exception as exc:
            raise Exception('Initialization error - {}'.format(exc))

        try:
            os.remove('server.stop')
        except Exception:
            pass

        while not self.should_stop():
            to_read, to_write, _ = select.select(
                self.sockets_to_read,
                self.sockets_to_write,
                self.sockets_with_exceptional_condition
            )

            for socket in to_read:
                self.process_socket(socket)

            time.sleep(0.01)

        self.stop()

    def stats(self):
        pass

    def dump_stats(self, key):
        if not self.connections[key]['bytes_received']:
            return
        address = '_'.join(map(str, self.connections[key]['address']))
        with open('{}_{}.stats'.format(self.__class__.__name__, address), 'w') as handle:
            handle.write('Protocol: {}\n'.format(self.protocol))
            handle.write('Mechanism: {}\n\n'.format(self.mechanism))
            handle.write('Messages received: {}\n\n'.format(self.connections[key]['messages_received']))
            handle.write('Bytes received: {}\n'.format(self.connections[key]['bytes_received']))

    def should_stop(self):
        return os.path.exists('server.stop')


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print(HELP_MESSAGE)
        sys.exit(0)

    assert len(sys.argv) == 5

    port, protocol, messages_size, mechanism = sys.argv[1:]

    try:
        port = int(port)
        messages_size = int(messages_size)
    except Exception:
        pass

    assert isinstance(port, int)
    assert isinstance(protocol, str)
    assert isinstance(messages_size, int)
    assert isinstance(mechanism, str)

    server = Server(
        port=port,
        protocol=protocol,
        messages_size=messages_size,
        mechanism=mechanism
    )
    server.run()
