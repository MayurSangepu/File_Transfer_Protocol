import socket
from struct import pack, unpack
from random import randint
from utils import Utils

'''
Acknowledgement: Some of the code in this file is written by referencing online sources for 
                packing and unpacking data to send over sockets.
'''

class TCPServer:
    def __init__(self, client, server, option=None) -> None:
        """
        Initialize the server
        :param client:
        :param server:
        :param option:
        """
        self.client = client
        self.server = server
        self.tries = 3
        self.seq = 0
        self.next_expected = 0
        self.data = {}
        self.filename = None
        self.option = option
        self.dropped_once = False
        self.seqnum = 0
        self.util = Utils(client, server)
        self.sockListen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sockSend = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.newreq = False
        try:
            self.sockListen.bind((self.server.getAddress(), int(self.server.getPort())))
        except:
            pass
        self.startServer()

    def __str__(self):
        return f'Client: {self.client} Server: {self.server}'

    def __repr__(self):
        return f'Client: {self.client} Server: {self.server}'

    def startServer(self):
        """
        Start the server
        :return:
        """
        print('TCP server endpoint started listening')
        while True:
            if self.seqnum == 0:
                self.seqnum = 1
            data, addr = self.sockListen.recvfrom(1024)
            tcp_header = data[:16]
            header = unpack('2i5bH', tcp_header)

            if self.util.check_packet_type(header, 'is_syn_packet'):
                if self.newreq:
                    self.seqnum = 1
                self.seq = randint(0, 100)
                self.next_expected = self.util.send_SYNACK(self.seq, header[0], self.sockSend)

            elif header[3] == 1:
                print('Received SYNACK acknowledgement, sending ACK')
                self.next_expected = header[0]+1

            elif self.util.check_packet_type(header, 'is_wrq_request'):
                if not self.newreq:
                    self.seqnum = 1
                seq = header[0]
                ack = 0
                d = data[16:]
                wrq = pack('2i5bH', seq, ack, 0, 0, 0, 1, 0, 0)
                checksum_value = self.util.compute_checksum(wrq + d)
                if header[7] == checksum_value:
                    if self.newreq:
                        self.seqnum = 1
                    self.filename = data[16:].decode().strip()
                    print('write request received from client for file '+self.filename)
                    self.next_expected = header[0]+1
                    if self.seqnum == 0:
                        self.seqnum = 1
                    self.util.send_ACK(self.seq + 1, self.next_expected, self.sockSend, self.client)
                    self.seq += 1
                    self.data = {}
                else:
                    print('Checksum not matching.')

            elif self.util.check_packet_type(header, 'is_rrq_request'):
                seq = header[0]
                if self.seqnum == 0:
                    self.seqnum = 1
                ack = 0
                d = data[16:]
                wrq = pack('2i5bH', seq, ack, 0, 0, 0, 0, 1, 0)
                checksum_value = self.util.compute_checksum(wrq + d)
                if self.newreq:
                    self.seqnum = 1
                if header[7] == checksum_value:
                    self.filename = data[16:].decode().strip()
                    if self.seqnum == 0:
                        self.seqnum = 1
                    print('read request received from client for file '+self.filename)
                    self.util.send_ACK(self.seq + 1, seq, self.sockSend, self.client)
                    self.seq += 1
                    self.data = {}
                else:
                    print('Checksum not matching.')
                is_valid = False
                fname = self.filename
                fname = fname.split('/')[-1]
                fname = 'server/' + fname
                with open(fname, 'rb') as f:
                    data = f.read()
                if len(data) > 0:
                    is_valid = True
                packets = self.util.divide_into_packets(data, 512)
                self.util.send_file(packets, self.seq + 1, self.sockSend, self.sockListen, self.client)

            elif self.util.check_packet_type(header, 'is_fin_packet'):
                print('Client initiated FIN packet')
                complete_data = bytearray(b'')
                if self.newreq:
                    self.seqnum = 0
                for i in sorted(self.data.keys()):
                    if self.seqnum > 1:
                        continue
                    packet = unpack('H512s', bytearray(self.data[i]))
                    data_size = packet[0]
                    complete_data += packet[1][:data_size]
                if self.seqnum == 0:
                    self.seqnum = 1
                fname = self.filename
                fname = fname.split('/')[-1]
                import os
                if not os.path.exists('server'):
                    os.makedirs('server')
                is_valid = False
                fname = 'server/' + fname
                if not os.path.exists(fname):
                    open(fname, 'w').close()
                with open(fname, 'wb') as f:
                    f.write(complete_data)
                print('File transfer complete')

            elif self.util.check_packet_type(header, 'is_data_packet'):
                seq = header[0]
                ack = 0
                if self.seqnum == 0:
                    self.seqnum = 1
                d = data[16:]
                pkt = pack('2i5bH', seq, ack, 0, 0, 0, 0, 0, 0)
                if self.newreq:
                    self.seqnum = 1
                checksum_value = self.util.compute_checksum(pkt + d)
                if self.next_expected == header[0]:
                    if header[7] == checksum_value:
                        d = data[16:]
                        if self.newreq:
                            self.seqnum = 1
                        self.data[seq] = d
                        self.next_expected = seq+1
                        self.seq += 1
                        if self.seqnum == 0:
                            self.seqnum = 1
                        if self.option == 'da' and not self.dropped_once:
                            self.util.send_ACK(self.seq, self.next_expected, self.sockSend, self.client, True)
                            self.dropped_once = True
                        else:
                            self.util.send_ACK(self.seq, self.next_expected, self.sockSend, self.client)
                    else:
                        print('Checksum not matching ')
                else:
                    self.seq += 1
                    self.util.send_ACK(self.seq, self.next_expected, self.sockSend, self.client)
