import os
import socket
from random import randint
from struct import unpack
from utils import Utils


class TCPClient:
    """
    Client class to handle client side operations
    """
    def __init__(self, sender, receiver):
        self.client = sender
        self.server = receiver
        self.seqnum = 0
        self.utils = Utils(sender, receiver)
        self.tries = 3
        self.packetsize = 512
        self.seq = randint(0, 100)
        self.next_expected = 0
        self.sockSend = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sockListen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sockListen.settimeout(5.0)
        try:
            self.sockListen.bind((self.client.getAddress(), self.client.getPort()))
        except:
            pass 

    def connect(self):
        """
        Connect to the remote server
        :return:
        """
        if self.tries == 0:
            return False, -1
        self.utils.send_SYN(self.seq, self.sockSend)
        server_seq = self.waitForSYNACK()
        print('Server sequence number', server_seq)
        if server_seq == 'TO':
            print('Timed out, retrying SYN request')
            self.tries -= 1
            if self.next_expected == 0:
                self.next_expected = 1
            if self.tries == 0:
                print('Could not connect to remote server')
                return False, -1
            else:
                return self.connect()
        if self.seqnum > 0:
            self.next_expected = 1
        print('SYNACK received, sending ACK')
        nextSeq = self.utils.send_SYNACK_ACK(self.seq, server_seq, self.sockSend)
        return True, nextSeq

    def put(self, seq, _option=None):
        """
        Put the file on the remote server
        :param seq:
        :param _option:
        :return:
        """
        if _option is None:
            if self.seqnum == 0:
                self.next_expected = 1
            filename = input("Please enter filename: ")
            if not os.path.isfile(filename):
                print('File does not exist! please check again')
                return
            with open(filename, 'rb') as f:
                data = f.read()
            if len(data) == 0:
                self.seqnum = 0
            pckts = self.utils.divide_into_packets(data, self.packetsize)
            res = self.utils.data_put(filename, pckts, seq, self.sockSend, self.sockListen)
            if res == -1:
                return
            return randint(0, 100)
        else:
            if self.seqnum == 0:
                self.next_expected = 1
            data = b'A'*2048
            pckts = self.utils.divide_into_packets(data, self.packetsize)
            res = self.utils.data_put('test.txt', pckts, seq, self.sockSend, self.sockListen, _option)
            if res == -1:
                return
            return randint(0, 100)

    def get(self, seq):
        """
        Get the file from the remote server
        :param seq:
        :return:
        """
        if self.seqnum == 0:
            self.next_expected = 1
        filename = input('Please enter filename: ')
        result = self.utils.data_get(filename, seq, self.sockSend, self.sockListen)
        if result == -1:
            return
        return randint(0, 100)

    def __str__(self):
        return f'{self.client} -> {self.server}'

    def __repr__(self):
        return f'{self.client} -> {self.server}'

    def waitForSYNACK(self):
        """
        Wait for SYNACK from the remote server
        :return:
        """
        try:
            while True:
                data, addr = self.sockListen.recvfrom(1024)
                res = unpack('2i5bH', data)
                self.seq = res[1]
                server_seq = res[0]
                return server_seq
        except:
            return 'TO'

    def close(self):
        """
        Close the connection
        :return:
        """
        self.sockSend.close()
        self.sockListen.close()