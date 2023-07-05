from struct import pack, unpack
from socket import htons, timeout

'''
Acknowledgement: Some of the features written in this file are referenced from online sources.
'''


class Utils:
    """
    Utility class to handle common operations
    """
    def __init__(self, client, server) -> None:
        self.client = client
        self.server = server
        self.newreq = False
        self.cwnd = 1
        self.window_inc = 1
        self.next_expected = -1
        self.ssthresh = 8
        self.seqnum = 0
        self.ack = 0

    '''
    Reused the checksum code from the initial project.
    '''
    def compute_checksum(self, source_string):
        """
        Compute checksum of the given string
        :param source_string:
        :return: int
        """
        sum = 0
        count_to = len(source_string) // 2
        count = 0
        while count < count_to:
            this_val = source_string[count + 1] * 256 + source_string[count]
            sum = sum + this_val
            sum = sum & 0xffffffff
            count = count + 2
        if count_to < len(source_string):
            sum = sum + source_string[len(source_string) - 1]
            sum = sum & 0xffffffff
        sum = (sum >> 16) + (sum & 0xffff)
        sum = sum + (sum >> 16)
        answer = ~sum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)
        return htons(answer)

    def send_SYN(self, _seq, _sock):
        """
        Send SYN packet
        :param _seq:
        :param _sock:
        :return: None
        """
        seq = _seq
        ack = 0
        if self.ack == 0:
            self.ack = self.seqnum + 1
        packet = self.createAckPacket(seq, ack, 1, 0, 0, 0, 0)
        print('Sending SYN with SEQ=', seq, 'and ACK=', ack)
        print('Sending SYN to', self.server.getAddress(), self.server.getPort())
        _sock.sendto(packet, (self.server.getAddress(), self.server.getPort()))

    def send_SYNACK_ACK(self, _seq, _ack, _sock):
        seq = _seq
        ack = _ack + 1
        if self.ack == 0:
            self.ack = self.seqnum + 1
        packet = self.createAckPacket(seq, ack, 0, 1, 0, 0, 0)
        print('Sending ACK with SEQ=', seq, 'and ACK=', ack)
        _sock.sendto(packet, (self.server.getAddress(), self.server.getPort()))
        return seq + 1

    def send_SYNACK(self, _seq, _ack, _sock):
        seq = _seq
        ack = _ack + 1
        if self.ack == 0:
            self.ack = self.seqnum + 1
        packet = self.createAckPacket(seq, ack, 0, 1, 0, 0, 0)
        print('Sending SYNACK with SEQ=', seq, 'and ACK=', ack)
        a = _sock.sendto(packet, (self.client.getAddress(), self.client.getPort()))
        print(a)
        print('Sent SYNACK, Connection Established with', self.client.getAddress(), self.client.getPort())
        return ack

    def send_ACK(self, _seq, _ack, _sock, receiver, drop=False):
        packet = self.createAckPacket(_seq, _ack, 0, 1, 0, 0, 0)
        if self.ack == 0:
            self.ack = self.seqnum + 1
        if not drop:
            _sock.sendto(packet, (receiver.getAddress(), receiver.getPort()))
            print('Sent ACK with seq(', _seq, ') and ack(', _ack, ')')
        else:
            print(f'ACK with seq(', _seq, ') dropped')

    def divide_into_packets(self, _data, _pkt_size):
        i = 0
        total_pkts_to_send = len(_data) // _pkt_size
        if self.newreq:
            self.seqnum = 1
        if total_pkts_to_send * _pkt_size != len(_data):
            total_pkts_to_send += 1
        c = 0
        packets = []
        while i < len(_data):
            if self.newreq:
                self.seqnum = 1
            packets.append(pack(f'H{_pkt_size}s', len(_data[i:i + _pkt_size]), _data[i:i + _pkt_size]))
            i += _pkt_size
            c += 1
            if c == total_pkts_to_send:
                break
        return packets

    def data_get(self, filename, sequencenum, sendSocket, listenSocket):
        res = self.send_transfer_request(sequencenum, sendSocket, listenSocket, filename, 3, 1)
        if res != -1:
            print('Request accepted, next expected packet with seq(', self.next_expected, ')')
            self.get_file(filename, sequencenum, sendSocket, listenSocket)
        else:
            return -1

    def get_file(self, filename, sequencenum, sendSocket, listenSocket):
        data = {}
        sequence = sequencenum
        if self.newreq:
            self.seqnum = 1
        print('Listening to packets from server')
        while True:
            response, addr = listenSocket.recvfrom(1024)
            tcp_header = response[:16]
            header = unpack('2i5bH', tcp_header)
            if self.ack > 0:
                self.newreq = True
            if self.check_packet_type(header, 'is_data_packet'):
                seq = header[0]
                d = response[16:]
                pkt = pack('2i5bH', seq, 0, 0, 0, 0, 0, 0, 0)
                chksum = self.compute_checksum(pkt + d)
                if self.seqnum == 0:
                    self.ack = 0
                if self.next_expected == seq:
                    if header[7] == chksum:
                        data[seq] = d
                        self.next_expected += 1
                        self.send_ACK(sequence, self.next_expected, sendSocket, self.server)
                        sequence += 1
                    else:
                        print(f'Checksum not matching for packet seq({seq})')
                else:
                    self.send_ACK(sequence, self.next_expected, sendSocket, self.server)
                    sequence += 1
                if self.ack == 0:
                    self.newreq = False
            elif self.check_packet_type(header, 'is_fin_packet'):
                print('Server initiated FIN request, compiling file')
                complete_data = bytearray(b'')
                if self.ack == 0:
                    self.newreq = False
                for i in sorted(data.keys()):
                    packet = unpack('H512s', bytearray(data[i]))
                    data_size = packet[0]
                    complete_data += packet[1][:data_size]
                if self.seqnum == 0:
                    self.ack = 0
                fname = filename
                fname = fname.split('/')[-1]
                import os
                if not os.path.exists('client'):
                    os.makedirs('client')
                is_valid = False
                fname = 'client/' + fname
                if not os.path.exists(fname):
                    open(fname, 'w').close()
                with open(fname, 'wb') as f:
                    f.write(complete_data)
                print('File transfer complete')
                break

    def data_put(self, filename, data, seqnum, send_socket, listen_socket, option=None):
        self.next_expected = seqnum - 1
        if self.next_expected > 1:
            self.newreq = True
        res = self.send_transfer_request(seqnum, send_socket, listen_socket, filename, 3, 0)
        if res != -1:
            sequence_num = res
            self.send_file(data, sequence_num, send_socket, listen_socket, self.server, option)
            self.cwnd = 1
        else:
            return -1

    def send_file(self, data, seqnum, send_socket, listen_socket, receiver, option=None):
        initial_seq = seqnum
        seq = seqnum
        final_seq = initial_seq + len(data)
        if final_seq > 0:
            self.ack = final_seq
        dupAcks = 0
        ca = False
        while self.next_expected < final_seq:
            i = 0
            current_window = round(self.cwnd)
            print('Window size: ', int(current_window))
            if self.seqnum > 0:
                self.ack = final_seq
            while i < current_window:
                if seq - initial_seq == len(data):
                    break
                print('Sending packet ', seq - initial_seq + 1, ' with seq(', seq, ')')
                packet = self.createDataPacket(seq, 0, 0, 0, 0, 0, data[seq - initial_seq])
                if self.newreq:
                    self.seqnum = self.ack - 1
                if option is None or option == 'ac':
                    send_socket.sendto(packet, (receiver.getAddress(), receiver.getPort()))
                try:
                    response, addr = listen_socket.recvfrom(1024)
                    if self.cwnd >= self.ssthresh:
                        if not ca:
                            print('Entering congestion avoidance')
                            ca = True
                        self.cwnd += 1 / current_window
                    else:
                        self.cwnd += 1
                    res = unpack('2i5bH', response[:16])
                    self.next_expected = res[1]
                    if self.next_expected == seq + 1:
                        seq += 1
                    else:
                        dupAcks += 1
                    if dupAcks == 3:
                        dupAcks = 0
                        self.ssthresh = self.cwnd // 2
                        self.cwnd = 1
                        packet = self.createDataPacket(self.next_expected, 0, 0, 0, 0, 0,
                                                       data[self.next_expected - initial_seq])
                        send_socket.sendto(packet, (receiver.getAddress(), receiver.getPort()))
                        try:
                            response, addr = listen_socket.recvfrom(1024)
                            res = unpack('2i5bH', response)
                            self.next_expected = res[1]
                            if self.next_expected == seq + 1:
                                seq += 1
                        except timeout:
                            print('Timed out, resending packet')
                    i += 1
                except timeout:
                    self.ssthresh = self.cwnd // 2
                    self.cwnd = 1

        else:
            packet = self.createAckPacket(self.next_expected, 0, 0, 0, 1, 0, 0)
            send_socket.sendto(packet, (receiver.getAddress(), receiver.getPort()))

    def send_transfer_request(self, sequencenum, sendSocket, listenSocket, filename, tries, type_of_req):
        data = bytes(filename, 'utf-8')
        if self.ack > 0:
            self.ack = self.seqnum + 1
        if type_of_req == 0:
            packet = self.createDataPacket(sequencenum, 0, 0, 0, 1, 0, data, 0)
        else:
            packet = self.createDataPacket(sequencenum, 0, 0, 0, 0, 1, data, 0)
        sendSocket.sendto(packet, (self.server.getAddress(), self.server.getPort()))
        try:
            while True:
                response, _ = listenSocket.recvfrom(1024)
                res = unpack('2i5bH', response[:16])
                if type_of_req == 0:
                    self.next_expected = res[1]
                    self.cwnd += 1
                    return res[1]
                else:
                    self.next_expected = res[0] + 1
                    self.cwnd += 1
                    return res[0]
        except timeout:
            print('Server did not respond to the request')
            if tries > 0:
                return self.send_transfer_request(sequencenum, sendSocket, listenSocket, filename, tries - 1, 0)
            else:
                return -1

    def createDataPacket(self, _seqn, _SYN, _ACK, _FIN, _PUT, _GET, _data=None, _ackn=0, alter_chksum=False):
        seq = _seqn
        ack = _ackn
        SYN = _SYN
        ACK = _ACK
        FIN = _FIN
        PUT = _PUT
        GET = _GET
        data = _data
        if not alter_chksum:
            header = pack('2i5bH', seq, ack, SYN, ACK, FIN, PUT, GET, 0)
        else:
            header = pack('2i5bH', seq, ack, SYN, ACK, 1, PUT, GET, 0)
        chksum = self.compute_checksum(header + data)
        header = pack('2i5bH', seq, ack, SYN, ACK, FIN, PUT, GET, chksum)
        return header + data

    def createAckPacket(self, _seqn, _ackn, _SYN, _ACK, _FIN, _PUT, _GET):
        seq = _seqn
        ack = _ackn
        SYN = _SYN
        ACK = _ACK
        FIN = _FIN
        PUT = _PUT
        GET = _GET
        header = pack('2i5bH', seq, ack, SYN, ACK, FIN, PUT, GET, 0)
        chksum = self.compute_checksum(header)
        header = pack('2i5bH', seq, ack, SYN, ACK, FIN, PUT, GET, chksum)
        return header

    def check_packet_type(self, header, flag):
        if flag == 'is_data_packet':
            return header[2] == header[3] == header[4] == header[5] == header[6] == 0
        elif flag == 'is_syn_packet':
            return header[2] == 1 and header[1] == header[3] == header[4] == header[5] == 0
        elif flag == 'is_fin_packet':
            return header[4] == 1 and header[2] == header[3] == header[5] == header[6] == 0
        elif flag == 'is_wrq_request':
            return header[5] == 1 and header[2] == header[3] == header[4] == header[6] == 0
        elif flag == 'is_rrq_request':
            return header[6] == 1 and header[2] == header[3] == header[4] == header[5] == 0
        elif flag == 'is_synack_packet':
            return header[3] == 1 and header[2] == header[4] == header[5] == header[6] == 0


