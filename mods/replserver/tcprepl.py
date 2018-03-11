import SocketServer
from time import sleep

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
        self.telnet = telnetproto.TelnetProtocol()

   
    def finish(self):
        super(ReplRequestHandler, self).finish()
        logger.logInfo('REPL connection close')

    def echo(self, msg):
        lines = str(msg).replace('\n', NEWLINE) 
        self.__write(lines + NEWLINE)

    def __recv(self):
        while True:
            data = self.request.recv(1024)
            logger.logDebug('RECV({}): {}'.format(len(data), repr(data)))
            if len(data) == 0:
                return None
            if data[0] == b'\xff':
                if data[1] == b'\xec':  # TELNET linemode EOF
                    return None
                self.__write(self.telnet.negotiation(data))
                if self.prompt is None:
                    self.prompt = TELNET_PROMPT
                    self.__write(self.prompt)
                continue
            elif data[0] == b'\x04':
                return None
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
        data = None
        while True:
            self.__write(self.telnet.negotiation(data))
            termtype = self.telnet.getState('TERM')
            if termtype is not None:
                break;
            data = self.request.recv(1024)
        if termtype =='REPLCLIENT':
            self.prompt = None
        sleep(0.5)  # adhoc: prevent packet integration
        self.echo(self.greeting + ', TERM={}'.format(termtype))
        while True:
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
