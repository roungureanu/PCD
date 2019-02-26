import abc
import sys
import logging


class BaseWorker(abc.ABC):
    PROTOCOLS = {
        'TCP': 'TCP',
        'UDP': 'UDP'
    }
    MECHANISMS = {
        'STREAMING': 'STREAMING',
        'STOP-AND-WAIT': 'STOP-AND-WAIT'
    }
    ACKNOWLEDGEMENT_MESSAGE = b'OK'
    STOP_MESSAGE = b'STOP'

    def __init__(self):
        self.logger = self._retrieve_logger()

        self.protocol = None
        self.mechanism = None

    def initialize(self):
        if self.protocol not in self.PROTOCOLS:
            raise Exception('Invalid protocol.')

        if self.mechanism not in self.MECHANISMS:
            raise Exception('Invalid mechanism')

    def _retrieve_logger(self):
        logger = logging.getLogger()

        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '[%(asctime)-15s] - [%(levelname)s - %(filename)s - %(threadName)s] %(message)s'
        )

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)

        file_handler = logging.FileHandler('{}.log'.format(self.__class__.__name__))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

        return logger

    def stop(self):
        self.logger.info('Stopping.')
        self.logger.info('Dumping stats.')
        self.stats()
        self.logger.info('Done dumping stats.')

    @abc.abstractmethod
    def run(self):
        pass

    @abc.abstractmethod
    def stats(self):
        pass
