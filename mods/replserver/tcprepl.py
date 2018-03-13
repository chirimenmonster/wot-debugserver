import os
import sys
import errno
import socket
import SocketServer
import io

import wotdbg
import telnetproto
from logger import logger

HOST = '127.0.0.1'
PORT = 2222

NEWLINE = '\r\n'
TELNET_PROMPT = '> '
TELNET_GOAHEAD = telnetproto.CODE['IAC'] + telnetproto.CODE['GA']

MOD_ID = '${mod_id}'
MOD_VERSION = '${version}'

class ReplRequestHandler(SocketServer.BaseRequestHandler, object):

    def setup(self):
        super(ReplRequestHandler, self).setup()
        logger.logInfo('REPL connection start')
        wotdbg.echo = self.__echo
        self.local_vars = { 'echo': self.__echo, 'wotdbg': wotdbg }
        self.telnet = telnetproto.TelnetProtocol(self.__repl)
        self.__buffer = ''
        self.greeting = 'welcome to WoT REPL interface, {}, {}'.format(MOD_ID, MOD_VERSION)

    def finish(self):
        super(ReplRequestHandler, self).finish()
        logger.logInfo('REPL connection close')

    def __echo(self, msg):
        if msg is None:
            return
        lines = str(msg).replace('\n', NEWLINE) 
        self.__write(lines + NEWLINE)

    def __recv(self):
        data = self.request.recv(2048)
        logger.logDebug('RECV({}): {}'.format(len(data), repr(data)))
        if len(data) == 0 and self.request.gettimeout() is None:
            raise socket.error(errno.ECONNRESET, os.strerror(errno.ECONNRESET))
        self.__buffer += data
        return self.__buffer

    def __process_telnet_command(self):
        while True:
            self.__buffer, codes = self.telnet.split(self.__buffer)
            if not codes:
                return self.__buffer
            elif codes[1] == telnetproto.CODE['EOF']:     # TELNET linemode EOF
                raise socket.error(errno.ECONNRESET, os.strerror(errno.ECONNRESET))
            else:
                self.__write(self.telnet.negotiation(codes))

    def __readline(self):
        while True:
            self.__process_telnet_command()
            i = self.__buffer.find('\n')
            if i >= 0:
                break
            self.__recv()
        result = self.__buffer[0:i+1]
        self.__buffer = self.__buffer[i+1:]
        return result

    def __write(self, data):
        if data is None or len(data) == 0:
            return
        logger.logDebug('SEND({}): {}'.format(len(data), repr(data)))
        self.request.sendall(data)

    def __repl(self, data):
        if data is None or len(data) == 0:
            return None
        logger.logDebug('REPL({}): {}'.format(len(data), repr(data)))
        try:
            sys.stdout = io.BytesIO()
            sys.stdin = open(os.devnull, 'r')
            try:
                result = str(eval(data, self.local_vars))
            except SyntaxError:
                exec data in self.local_vars
                result = ''
        except Exception:
            import traceback
            result = traceback.format_exc()
        finally:
            sys.stdin = sys.__stdin__
            sys.stdout = sys.__stdout__
            result += buffer.getvalue()
            if len(result) == 0:
                result = None
        if result is not None:
            logger.logDebug('REPL({}): {}'.format(len(result), repr(result)))
        return result

    def __negotiation(self):
        try:
            self.request.settimeout(1)
            self.__write(self.telnet.negotiation(None))
            while True:
                self.__process_telnet_command()
                self.__recv()
        except socket.timeout:
            pass
        finally:
            self.request.settimeout(None)

    def __mainloop(self):
        termtype = self.telnet.getState('TERM')
        self.__echo(self.greeting + ', TERM={}'.format(termtype))
        if termtype == 'REPLCLIENT':
            self.prompt = TELNET_GOAHEAD
        else:
            self.prompt = TELNET_PROMPT
        while True:
            self.__write(self.prompt)
            line = self.__readline().strip()
            if line == 'QUIT':
                raise socket.error(errno.ECONNRESET, os.strerror(errno.ECONNRESET))
            self.__echo(self.__repl(line))

    def handle(self):
        try:
            self.__negotiation()
            self.__mainloop()
        except socket.error as err:
            if err.args[0] == errno.ECONNRESET:
                logger.logInfo(err.args[1])
                self.__echo('\n' + 'connection closing...')
                return
            raise socket.error(err)

def runReplServer():
    server = SocketServer.TCPServer((HOST, PORT), ReplRequestHandler)
    logger.logDebug('REPL server start')
    server.serve_forever()


if __name__ == '__main__':
    logger.DEBUG = True
    MOD_ID = 'tcpreply'
    MOD_VERSION = 'test version'

    runReplServer()
