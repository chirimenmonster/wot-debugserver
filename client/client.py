#!/usr/bin/python

import socket

HOST = '127.0.0.1'
PORT = 2222

NEWLINE = '\r\n'
READYMSG = '~~~ok!~~~'


class SocketClose(Exception):
    pass


class Connection(object):

    def __init__(self, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        self.socket = s
        self.buffer = ''
        self.fake_telnet_negotiation()

    def __recv(self):
        data = self.socket.recv(1024)
        if len(data) == 0:
            return None
        return data

    def __readline(self):
        while True:
            i = self.buffer.find('\n')
            if i >= 0:
                break
            data = self.__recv()
            print repr(data)
            if data is None:
                return None
            self.buffer += data
            while self.strip_telnet_command():
                pass
        result = self.buffer[0:i+1]
        self.buffer = self.buffer[i+1:]
        return result

    def __write(self, data):
        if len(data) == 0:
            return
        self.socket.sendall(data)

    def fake_telnet_negotiation(self):
        # IAC WILL terminal-type
        self.__write(b'\xff\xfb\x18')
        # IAC DO new-environ
        self.__write(b'\xff\xfd\x27')
        # IAC SB terminal-type IS REPLCLIENT IAC SE
        self.__write(b'\xff\xfa\x18\x00REPLCLIENT\xff\xf0')

    def strip_telnet_command(self):
        k = self.buffer.find('\n')
        if k < 0:
            k = None
        i = self.buffer.find(b'\xff', 0, k)
        n = len(self.buffer)
        if i >= 0:
            if n > i + 1:
                c = self.buffer[i+1]
                if c in b'\xf1\xf2x\f3x\f4x\xf5\xf6\xf7\xf8\xf9':
                    if n > i + 2:
                        self.buffer = self.buffer[:i] + self.buffer[i+2:]
                elif c in b'\xfb\xfc\xfd\xfe':
                    if n > i + 3:
                        self.buffer = self.buffer[:i] + self.buffer[i+3:]
                elif c in b'\xfa':
                    j = self.buffer.find(b'\xff\xf0', i)
                    if j > 0:
                        self.buffer = self.buffer[:i] + self.buffer[j+2:]
                else:
                    raise ValueError
            return True
        else:
            return False

    def getGreeting(self):
        print self.__readline().rstrip()

    def exec_sync(self, cmd):
        self.__write(cmd + NEWLINE)
        result = []
        while True:
            line = self.__readline().rstrip()
            if line == READYMSG:
                return result
            result.append(line)
        raise SocketClose()

    def exec_sync_print(self, cmd):
        result = self.exec_sync(cmd)
        for line in result:
            print line


class Completer(object):

    def __init__(self, connection):
        self.connection = connection 
        self.clear_cache()

    def clear_cache(self):
        self.__cache = {}

    def cache_val(self, v, f):
        if v not in self.__cache:
            self.__cache[v] = f()
        return self.__cache[v]

    def get_locals(self):
        return self.connection.exec_sync("echo('\\n'.join(locals().keys()))")

    def get_dir(self, code):
        return self.connection.exec_sync("echo('\\n'.join(dir(%s)))" % code)

    def get_path_dir(self, locs, path):
        attrs = locs
        for i, token in enumerate(path):
            if token in attrs:
                attrs = self.get_dir('.'.join(path[0:i+1]))
            else:
                return []
        return attrs

    def completer(self, text, state):
        if text == '':
            return None
        try:
            locs = self.cache_val('locals', self.get_locals)
            if '.' in text:
                tokens = text.split('.')
                start = tokens[0:-1]
                last = tokens[-1]

                name = 'dir_' + '.'.join(start)
                attrs = self.cache_val(name, lambda: self.get_path_dir(locs, start))
                
                suggestion = [ w for w in attrs if w.startswith(last) ][state]
                return '.'.join(start + [suggestion])
            else:
                return [ w for w in locs if w.startswith(text) ][state]
        except IndexError:
            return None


def main():
    connection = Connection(HOST, PORT)
    completer = Completer(connection)
    
    try:
        import readline
        readline.set_completer(completer.completer)
        readline.parse_and_bind('tab: complete')
    except ImportError:
        pass

    try:
        connection.getGreeting()
        connection.exec_sync_print('__READYMSG = "%s"' % READYMSG)

        while True:
            try:
                completer.clear_cache()
                cmd = raw_input('> ')
                connection.exec_sync_print(cmd.strip())
            except EOFError:
                break

    except SocketClose:
        pass
    print 'connection closed'


if __name__ == "__main__":
    main()
