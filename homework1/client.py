import sys
import time
import socket

try:
    import homework1.base as base
except Exception:
    import base


HELP_MESSAGE = 'Usage: <script_name> <host> <port> <protocol> <messages_size> <mechanism>.\n' \
               '<host> - A string consisting of a domain name or an ip address.\n' \
               '<port> - A port number\n' \
               '<protocol> - A string equal to "TCP" or "UDP"\n' \
               '<messages_size> - An integer representing the size of the messages sent\n' \
               '<mechanism> - A equal to "STREAMING" or "STOP-AND-WAIT"\n'


KB = 1024
MB = 1024 * KB

TO_SEND = 10 * MB


class Client(base.BaseWorker):
    PROTOCOLS = {
        'TCP': 'TCP',
        'UDP': 'UDP'
    }
    MECHANISMS = {
        'STREAMING': 'STREAMING',
        'STOP-AND-WAIT': 'STOP-AND-WAIT'
    }

    def __init__(self, host: str, port: int, protocol: str, messages_size: int, mechanism: str):
        super().__init__()

        self.host = host
        self.port = port
        self.protocol = protocol
        self.mechanism = mechanism
        self.messages_size = messages_size

        self.bytes_sent = 0
        self.messages_sent = 0

        self.server_address = (socket.gethostbyname(self.host), self.port)

        self.messages_to_send = TO_SEND // messages_size + 1

        self.buffer = b'1' * messages_size

        self.transmission_time = 0

    def initialize(self):
        super().initialize()

        if self.protocol == self.PROTOCOLS['TCP']:
            self.connection = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM
            )
            self.connection.connect(self.server_address)
            self.connection.settimeout(10)
        elif self.protocol == self.PROTOCOLS['UDP']:
            self.connection = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_DGRAM
            )
            self.connection.settimeout(10)

    def send_message_without_acknowledgement(self, buffer):
        if self.protocol == self.PROTOCOLS['TCP']:
            self.connection.send(buffer)
        elif self.protocol == self.PROTOCOLS['UDP']:
            self.connection.sendto(buffer, self.server_address)
        self.messages_sent = self.messages_sent + 1
        self.bytes_sent = self.bytes_sent + len(buffer)

    def received_acknowledgement(self):
        message, address = None, None
        if self.protocol == self.PROTOCOLS['TCP']:
            try:
                message = self.connection.recv(len(self.ACKNOWLEDGEMENT_MESSAGE))
                address = self.server_address
            except socket.timeout:
                pass
        elif self.protocol == self.PROTOCOLS['UDP']:
            try:
                message, address = self.connection.recvfrom(len(self.ACKNOWLEDGEMENT_MESSAGE))
            except socket.timeout:
                pass

        return message == self.ACKNOWLEDGEMENT_MESSAGE and address == self.server_address

    def send_message_with_acknowledgement(self, buffer):
        acknowledgement_received = False
        while not acknowledgement_received:
            self.send_message_without_acknowledgement(buffer)
            self.logger.info('Waiting for acknowledgement.')
            start_time = time.time()
            while not acknowledgement_received:
                acknowledgement_received = self.received_acknowledgement()

                if self.protocol == self.PROTOCOLS['TCP']:
                    time.sleep(0.01)
                else:
                    time.sleep(0.25)

                if time.time() - start_time >= 1:
                    self.logger.info(
                        'Acknowledgement not received for too much time. Resending message.'
                    )
                    break

        self.logger.info('Received acknowledgement.')

    def send_message(self, buffer):
        if self.mechanism == self.MECHANISMS['STREAMING']:
            self.send_message_without_acknowledgement(buffer)
        elif self.mechanism == self.MECHANISMS['STOP-AND-WAIT']:
            self.send_message_with_acknowledgement(buffer)

    def run(self):
        self.logger.info('Initializing')
        try:
            self.initialize()
        except Exception as exc:
            raise Exception('Initialization error - {}'.format(exc))

        self.logger.info('There are {} messages to send.'.format(self.messages_to_send))
        for i in range(self.messages_to_send):
            self.logger.info('Sending message {}'.format(i + 1))

            ts_before_message_send = time.time()
            self.send_message(self.buffer)
            self.transmission_time = self.transmission_time + time.time() - ts_before_message_send
            self.logger.info('Message sent.')
            time.sleep(0.01)

        self.send_message_with_acknowledgement(self.STOP_MESSAGE)
        self.stop()

    def stats(self):
        with open('{}.stats'.format(self.__class__.__name__), 'w') as handle:
            handle.write('Protocol: {}\n'.format(self.protocol))
            handle.write('Mechanism: {}\n\n'.format(self.mechanism))
            handle.write('Bytes to send: {}\n'.format(TO_SEND))
            handle.write('Messages to send: {}\n\n'.format(self.messages_to_send))
            handle.write(
                'Average message transmission time sent: {}\n'.format(
                    round(self.transmission_time / self.messages_sent, 12)
                )
            )
            handle.write('Bytes sent: {}\n'.format(self.bytes_sent))
            handle.write('Messages sent: {}\n'.format(self.messages_to_send))


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print(HELP_MESSAGE)
        sys.exit(0)

    assert len(sys.argv) == 6

    host, port, protocol, messages_size, mechanism = sys.argv[1:]

    try:
        port = int(port)
        messages_size = int(messages_size)
    except Exception:
        pass

    assert isinstance(host, str)
    assert isinstance(port, int)
    assert isinstance(protocol, str)
    assert isinstance(messages_size, int)
    assert isinstance(mechanism, str)

    server = Client(
        host=host,
        port=port,
        protocol=protocol,
        messages_size=messages_size,
        mechanism=mechanism
    )
    server.run()
