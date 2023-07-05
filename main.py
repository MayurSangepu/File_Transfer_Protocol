import sys
from TCPClient import TCPClient
from TCPServer import TCPServer

'''
authors: Mayur Reddy Sangepu
project: File Transfer Protocol
Please check the readme file for instructions to run the program
'''

class Host:
    """
    Host class to store address and port of client and server
    """
    def __init__(self, address, port) -> None:
        self.address = address
        self.port = port

    def getAddress(self):
        return self.address

    def getPort(self):
        return int(self.port)

    def __str__(self) -> str:
        return f'{self.address}:{self.port}'

    def __repr__(self) -> str:
        return f'{self.address}:{self.port}'


class Client:
    """
    Client class to handle client side operations
    """
    def __init__(self):
        self.seqnum = 0
        self.client = None
        self.server = None
        self.option = None
        self.TCPClient = None
        self.seq = 0
        self.isConnected = False
        self.parse_args()
        self.start_client()

    def set_option(self, option):
        self.option = option

    def get_option(self):
        return self.option

    def parse_args(self):
        """
        Parse command line arguments
        :return: None
        """
        for idx, arg in enumerate(sys.argv):
            if arg == "-c" or arg == "--client":
                self.client = Host(sys.argv[idx+1], sys.argv[idx+2])
            elif arg == "-s" or arg == "--server":
                self.server = Host(sys.argv[idx+1], sys.argv[idx+2])
            else:
                continue

    def start_client(self):
        """
        Start client side operations
        :return: None
        """
        while True:
            try:
                print('\nFTP>')
                print('Commands: \nc     Connect to receiver host')
                print('p     Send file\ng     Receive file\nq     Quit')
                input_command = input()
                if input_command == 'c':
                    if not self.isConnected:
                        self.TCPClient = TCPClient(self.client, self.server)
                        self.isConnected, self.seq = self.TCPClient.connect()
                        if self.isConnected:
                            print('Established connection successfully')
                        else:
                            self.TCPClient = None
                    else:
                        print('Connection already exists')
                if input_command == 'p':
                    if self.TCPClient is not None:
                        self.seq = self.TCPClient.put(self.seq, self.option)
                    else:
                        print('Please establish connection before sending file')
                if input_command == 'g':
                    if self.TCPClient is not None:
                        self.seq = self.TCPClient.get(self.seq)
                    else:
                        print('Please establish connection to receive file')
                if input_command == 'q':
                    break
            except Exception as e:
                print('Please enter valid command')

class Server:
    """
    Server class to handle server side operations
    """
    def __init__(self) -> None:
        self.option = None
        self.client = None
        self.seq = 0
        self.server = None
        self.TCPClient = None
        self.isConnected = False
        self.parse_args()
        self.start_server()

    def parse_args(self):
        """
        Parse command line arguments
        :return: None
        """
        for idx, arg in enumerate(sys.argv):
            if arg == "-c" or arg == "--client":
                self.client = Host(sys.argv[idx+1], sys.argv[idx+2])
            elif arg == "-s" or arg == "--server":
                self.server = Host(sys.argv[idx+1], sys.argv[idx+2])
            else:
                self.seq = 1
                self.isConnected = False
                continue

    def start_server(self):
        """
        Start server side operations
        :return:
        """
        TCPServer(self.client, self.server, self.option)


if __name__ == '__main__':
    try:
        if sys.argv[1] == '-client':
            Client()
        elif sys.argv[1] == '-server':
            Server()
    except Exception:
        print('Plaese enter valid arguments')
