import socket
import SocketServer

import wotdbg
import telnetproto
from logger import logger

HOST = '127.0.0.1'
PORT = 2222

NEWLINE = '\r\n'
TELNET_PROMPT = '> '

MOD_ID = '${mod_id}'
MOD_VERSION = '${version}'


class ReplRequestHandler(SocketServer.BaseRequestHandler, object):

    def setup(self):
        super(ReplRequestHandler, self).setup()
        logger.logInfo('REPL connection start')
        wotdbg.echo = self.echo
        self.local_vars = { 'echo': self.echo, 'wotdbg': wotdbg }
        self.readymsg = None
        self.buffer = ''
        self.greeting = 'welcome to WoT REPL interface, {}, {}'.format(MOD_ID, MOD_VERSION)
        self.prompt = TELNET_PROMPT
        self.telnet = telnetproto.TelnetProtocol(self.__repl)

   
    def finish(self):
        super(ReplRequestHandler, self).finish()
        logger.logInfo('REPL connection close')

    def echo(self, msg):
        lines = str(msg).replace('\n', NEWLINE) 
        self.__write(lines + NEWLINE)

    def __recv(self):
        while True:
            data = self.request.recv(2048)
            logger.logDebug('RECV({}): {}'.format(len(data), repr(data)))
            if len(data) == 0:
                return None
            data, codes = self.telnet.split(data)
            if codes is not None and len(codes) > 0:
                if codes[1] == telnetproto.CODE['EOF']:     # TELNET linemode EOF
                    return None
                self.__write(self.telnet.negotiation(codes))
            break
        return data

    def __readline(self):
        if self.prompt:
            self.__write(self.prompt)
        while True:
            i = self.buffer.find('\n')
            if i >= 0:
                break
            data = self.__recv()
            if data is None:
                return None
            self.buffer += data
        result = self.buffer[0:i+1]
        self.buffer = self.buffer[i+1:]
        return result

    def __write(self, data):
        if len(data) == 0:
            return
        logger.logDebug('SEND({}): {}'.format(len(data), repr(data)))
        self.request.sendall(data)
    
    def handle(self):
        data = ''
        self.__write(self.telnet.negotiation(None))
        self.request.settimeout(1)
        while True:
            try:
                data += self.request.recv(2048)
            except socket.timeout:
                break
            while True:
                data, codes = self.telnet.split(data)
                if codes is None:
                    break
                self.__write(self.telnet.negotiation(codes))
        self.request.settimeout(None)
        termtype = self.telnet.getState('TERM')
        if termtype =='REPLCLIENT':
            self.prompt = None
        self.echo(self.greeting + ', TERM={}'.format(termtype))
        while True:
            self.__write(telnetproto.CODE['IAC'] + telnetproto.CODE['GA'])
            line = self.__readline()
            if line == None:
                break
            line = line.strip()
            if line == 'QUIT':
                break
            if line.startswith('__READYMSG = '):
                vars = {}
                exec line in vars
                self.readymsg = vars.get('__READYMSG', None)
                self.echo(self.readymsg)
                continue
            self.repl(line)
            if self.readymsg is not None:
                self.echo(self.readymsg)
        if self.prompt:
            self.echo('connection closing...')

    def __repl(self, data):
        try:
            try:
                logger.logDebug('REPL({}): {}'.format(len(data), repr(data)))
                result = eval(data, self.local_vars)
                logger.logDebug('REPL({}): {}'.format(len(result), repr(result)))
                return result
            except SyntaxError:
                exec data in self.local_vars
        except Exception:
            import traceback
            self.echo(traceback.format_exc())           

    def repl(self, line):
        try:
            try:
                result = eval(line, self.local_vars)
                self.echo(result)
            except SyntaxError:
                exec line in self.local_vars
        except Exception:
            import traceback
            self.echo(traceback.format_exc())


def runReplServer():
    server = SocketServer.TCPServer((HOST, PORT), ReplRequestHandler)
    server.serve_forever()


if __name__ == '__main__':
    logger.DEBUG = True
    MOD_ID = 'tcpreply'
    MOD_VERSION = 'test version'
    runReplServer()
