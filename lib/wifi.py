
import network
# create config.py in the root folder
import config
import socket
from time import sleep
import machine

ssid = config.WIFI_SSID
password = config.WIFI_PASSWORD
wifiCheckSleepTimeSec = 5

class Wifi:
    wlan: network.WLAN = None
    ip: str = None
    socketOpened: socket = None

    def __init__(self, stayInLoop=True):
        self.stayInLoop = stayInLoop
        self.wlan = None
        self.ip = None
        self.socketOpened = None
        if self._handleConnectToWiFi():
            self.openSocket()

    """
    Method will try to connect to WiFi network by provided data in config.py.
    To handle the lack of WiFi network method will rise exception after 5 attempts in +- 5 seconds.
    Exception must be cached and connect method must be called again - for example in loop.
    This behavior is caused by the need to reuse the connect method from wlan module. 
    """
    def connect(self):
        # connect as client. AP_IF - make access point
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.ifconfig((config.IP_ADDRESS, config.SUBNET_MASK, config.GATEWAY, config.DNS))
        self.wlan.connect(ssid, password)
        connectionAttempts = 0
        while self.wlan.isconnected() == False:
            print('Waiting for connection...')
            sleep(1)
            connectionAttempts += 1
            print("Connection attempts: {}".format(connectionAttempts))
            if (connectionAttempts == 5):
                raise Exception("Maximum connection attempts reached")
        print(self.wlan.ifconfig())
        return self.wlan.ifconfig()[0]

    """
    Method will try to open the socket on port 80 and bind it to machine ip address.
    If any exception occur, machine will restart to release all resource. 
    After reboot main.py will be started again. 
    """
    def openSocket(self):
        try:
            self._delegateOpenSocket()
        except OSError as e:
            print("OS error cached...")
            if e.errno == 98:
                print("Error cached - address in use. Machine reset needed")
                sleep(5)
                machine.reset()
            else:
                print("Unknown error while trying to open socket. Machine reset needed")
                sleep(5)
                machine.reset()

    """
    Method will try to receive data from socket.
    If error will rise - socket might be closed.
    """
    def isSocketOpened(self) -> bool:
        print("Checking socket state...")
        try:
            self.socketOpened.settimeout(1.5)
            client = self.socketOpened.accept()[0].recv(1024)
            client.close()
            print("Socket is open")
            return True
        except OSError as oe:
            print("errno: {}".format(oe.errno))
            if oe.errno == 110:
                print("Timeout error cached. Socket should be open")
                return True
            print("Socket error - socket might be closed: {}".format(oe))
            return False


    """
    Method will check WiFi connection.
    Retry according to stayInLoop and open the server only when connected.
    """
    def checkConnection(self):
        if self.wlan is None or not self.wlan.isconnected():
            print("Wifi connection lost...")
            if self.socketOpened is not None:
                self.socketOpened.close()
                self.socketOpened = None
            self.ip = None
            if not self._handleConnectToWiFi():
                return False

        if self.ip is None:
            self.ip = self.wlan.ifconfig()[0]
        if self.socketOpened is None:
            self.openSocket()
        return True

    def _handleConnectToWiFi(self):
        print("Request for handle connect to WiFi. Starting loop...")
        while(self.wlan == None or not self.wlan.isconnected()):
            try:
                self.ip = self.connect()
            except Exception as ex:
                print("Connection error {}".format(ex))
                if not self.stayInLoop:
                    return False
        return True

    def _delegateOpenSocket(self):
            print("Try to open socket")
            address = (self.ip, 80)
            print("Creating socket")
            self.socketOpened = socket.socket()
            print("Binding address to the socket")
            self.socketOpened.bind(address)
            print("Setting socket to listen")
            self.socketOpened.listen(1)
            print(self.socketOpened)
