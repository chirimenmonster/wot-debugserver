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
        self.stream = s.makefile()
    
    def exec_sync(self, cmd):
        self.stream.write(cmd + NEWLINE)
        self.stream.flush()
        result = []
        for line in self.stream:
            line = line.rstrip()
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
        return self.connection.exec_sync("echo('\\r\\n'.join(locals().keys()))")

    def get_dir(self, code):
        return self.connection.exec_sync("echo('\\r\\n'.join(dir(%s)))" % code)

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
