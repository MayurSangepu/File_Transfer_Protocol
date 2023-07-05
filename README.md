# File_Transfer_Protocol

This is File transfer protocol implementation using UDP sockets.
### Usage
#### Client
```bash
 python3 main.py -client -c <client-ip> <client-port> -s <server-ip> <server-port>
 eg: python3 main.py -client -c localhost 8000 -s localhost 8001
```
#### Server
```bash
python3 main.py -server -c <client-ip> <client-port> -s <server-ip> <server-port>
eg: python3 main.py -server -c localhost 8000 -s localhost 8001
```
### Commands
#### Client
```bash
FTP>
Commands:
c     Connect to receiver host
p     Send file
g     Receive file
q     Quit
```

For put command, the client will be prompted to enter the file name. The file path should be absolute.
For get command, the client will be prompted to enter the file name. The file will be saved in the current directory.
The file path need not be absolute.
