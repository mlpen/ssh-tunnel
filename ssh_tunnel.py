import socket
import sys
import os
import subprocess
import time

timeout = 4
wait_time = 2
echo_interval = 2

def get_time():
    return time.asctime(time.localtime(time.time()))

class EchoConn():
    def __init__(self, server_addr, remote_port):
        self.server_addr = server_addr
        self.remote_port = remote_port

        print("%s Creating echo server..." % (get_time()), end = "")

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('', 0))
        addr, port = self.server.getsockname()
        self.server.listen(1)
        self.server.settimeout(timeout)
        self.local_port = port
        self.suppress_normal_echo_log = False

        self.client = None
        self.conn = None

        self.connected = False

        print("Completed")

    def connect(self):
        print("%s Connecting echo server through %s:%d..." % (get_time(), self.server_addr, self.remote_port), end = "")

        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((self.server_addr, self.remote_port))
            self.client.settimeout(timeout)

            conn, addr = self.server.accept()
            conn.settimeout(timeout)
            self.conn = conn

            print("Completed")

            self.connected = True
        except Exception as e:
            print("Failed")
            print("%s Exception: %s" % (get_time(), str(e)))

            self.connected = False

        return self.connected

    def send_echo(self):
        try:
            if not self.suppress_normal_echo_log:
                print("%s Testing connection: sending echo..." % (get_time()), end = "")

            timestamp = str(time.time())
            self.conn.send(timestamp.encode("ascii"))
            echo = self.client.recv(64)
            echo = echo.decode("ascii")
            match = timestamp == echo

            if not self.suppress_normal_echo_log:
                print("Match = %s" % (str(match)))

            self.suppress_normal_echo_log = True

            return match
        except socket.timeout as e:
            print("")
            print("%s Timeout: %s Loss connection" % (get_time(), str(e)))
            return False

    def disconnect(self):
        print("%s Closing echo connection..." % (get_time()), end = "")
        for to_close in [self.client, self.conn, self.server]:
            if to_close != None:
                to_close.close()
        print("Completed")


if __name__ == "__main__":
    def port_forward(username, server_addr, port_pairs):
        partial_cmd = []
        for pair in port_pairs:
            # mapping local port pair[0] to remote port pair[1]
            partial_cmd.extend(["-R", "%s:%d:localhost:%d" % (server_addr, pair[1], pair[0])])
        cmd = ["ssh", "-N", "-T"]  + partial_cmd + ["%s@%s" % (username, server_addr)]
        print("%s Forwarding ports %s..." % (get_time(), " ".join([str(pair[0]) + ":" + str(pair[1]) for pair in port_pairs])), end = "")
        proc = subprocess.Popen(cmd)
        time.sleep(wait_time)
        print("Completed")
        return proc

    username = sys.argv[1]
    server_addr = sys.argv[2]
    remote_echo_port = int(sys.argv[3])
    port_pairs = []
    for mapping in sys.argv[4:]:
        port_pairs.append(tuple([int(port) for port in mapping.split(':')]))

    while True:
        try:
            echo = EchoConn(server_addr, remote_echo_port)
            tunnel = port_forward(username, server_addr, [(echo.local_port, remote_echo_port)] + port_pairs)
            echo.connect()
        except Exception as e:
            print("%s Exception: %s" % (get_time(), str(e)))

        try:
            while echo.connected:
                if echo.send_echo():
                    time.sleep(echo_interval)
                else:
                    break
        except Exception as e:
            print("%s Exception: %s" % (get_time(), str(e)))

        try:
            echo.disconnect()
        except Exception as e:
            print("%s Exception: %s" % (get_time(), str(e)))

        try:
            tunnel.kill()
        except Exception as e:
            print("%s Exception: %s" % (get_time(), str(e)))

        try:
            time.sleep(wait_time)
        except Exception as e:
            print("%s Exception: %s" % (get_time(), str(e)))
