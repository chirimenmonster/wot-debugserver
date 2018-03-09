import SocketServer
import wotdbg
import datetime

HOST = '127.0.0.1'
PORT = 2222

NEWLINE = '\r\n'

GREETINGMSG = 'welcome to WoT REPL interface, {}, ver.{}'.format('${mod_id}', '${version}')

def __log(text):
    ds = datetime.time.strftime(datetime.datetime.now().time(), '%H:%M')
    print 'replserver %s: %s' % (ds, text)

try:
    import BigWorld
    log = lambda s: BigWorld.logInfo('${mod_id}', s, None)
except ImportError:
    log = __log

class ReplRequestHandler(SocketServer.StreamRequestHandler, object):

    def setup(self):
        super(ReplRequestHandler, self).setup()
        log('REPL connection start')
        wotdbg.echo = self.echo
        self.local_vars = { 'echo': self.echo, 'wotdbg': wotdbg }
        self.readymsg = None
    
    def finish(self):
        super(ReplRequestHandler, self).finish()
        log('REPL connection close')

    def echo(self, msg):
        self.rfile.write(str(msg) + NEWLINE)
        self.rfile.flush()

    def handle(self):
        self.echo(GREETINGMSG)
        while True:
            line = self.rfile.readline()
            if line == '':
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
    runReplServer()
