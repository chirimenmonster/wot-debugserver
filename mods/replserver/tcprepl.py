import socket
import wotdbg

BIND = '127.0.0.1'
PORT = 2222

NEWLINE = '\r\n'

GREETINGMSG = 'welcome to WoT REPL interface, {}, ver.{}'.format('${mod_id}', '${version}')

class Repl(object):

    def __init__(self, conn):
        self.conn = conn
        self.stream = conn.makefile()
        wotdbg.echo = self.echo
        self.local_vars = { 'echo': self.echo, 'wotdbg': wotdbg }
        self.readymsg = None

    def echo(self, s):
        self.stream.write(str(s) + NEWLINE)
        self.stream.flush()

    def start(self, once=False):
        self.echo(GREETINGMSG)
        for line in self.stream:
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
            if once:
                break

    def shutdown(self):
        self.stream.close()
        self.conn.close()

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


def run_repl():
    '''
    Run debug server until connection is closed
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((BIND, PORT))
    s.listen(1)

    conn, addr = s.accept()
    repl = Repl(conn)
    try:
        repl.start()
    except socket.error:
        pass

    repl.shutdown()
    s.close()


if __name__ == '__main__':
    run_repl()
