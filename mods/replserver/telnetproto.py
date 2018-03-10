
# Negotiation Protocol
TOKEN_SE    = b'\xf9'   # 240
TOKEN_SB    = b'\xfa'   # 250
TOKEN_WILL  = b'\xfb'   # 251
TOKEN_WONT  = b'\xfc'   # 252
TOKEN_DO    = b'\xfd'   # 253
TOKEN_DONT  = b'\xfe'   # 254
TOKEN_IAC   = b'\xff'   # 255

# Negotiation Options
TOKEN_ECHO              = b'\x01'   # 1
TOKEN_SUPPRESS_GO_AHEAD = b'\x03'   # 3
TOKEN_TERMINAL_TYPE     = b'\x18'   # 24
TOKEN_WINDOW_SIZE       = b'\x1f'   # 31
TOKEN_TERMINAL_SPEED    = b'\x20'   # 32
TOKEN_FLOW_CONTROL      = b'\x21'   # 33
TOKEN_LINE_MODE         = b'\x22'   # 34
TOKEN_ENVIRONMENT       = b'\x24'   # 36
TOKEN_NEW_ENVIRON       = b'\x27'   # 39

# Sub-negotiation Command
TOKEN_IS    = 0
TOKEN_SEND  = 1
TOKEN_INFO  = 2

# Negotiation Options CHARSET
TOKEN_CHARSET               = 42

# Negotiation Options NAWS
TOKEN_NAWS                  = 31

# Negotiation Options NEW-ENVIRON
TOKEN_NEW_ENVIRON_VAR       = 0
TOKEN_NEW_ENVIRON_VALUE     = 1
TOKEN_NEW_ENVIRON_ESC       = 2
TOKEN_NEW_ENVIRON_USERVAR   = 3

keyword = {
    TOKEN_SE:   'SE',
    TOKEN_SB:   'SB',
    TOKEN_WILL: 'WILL',
    TOKEN_WONT: 'WONT',
    TOKEN_DO:   'DO',
    TOKEN_DONT: 'DONT',
    TOKEN_IAC:  'IAC',
    TOKEN_ECHO:                 'echo',
    TOKEN_SUPPRESS_GO_AHEAD:    'suppress-go-ahead',
    TOKEN_TERMINAL_TYPE:        'terminal-type',
    TOKEN_WINDOW_SIZE:          'window-size',
    TOKEN_TERMINAL_SPEED:       'terminal-speed',
    TOKEN_FLOW_CONTROL:         'remote-flow-control',
    TOKEN_LINE_MODE:            'line-mode',
    TOKEN_ENVIRONMENT:          'environment',
    TOKEN_NEW_ENVIRON:          'new-environment',
}


acceptOptions = { TOKEN_SUPPRESS_GO_AHEAD, TOKEN_LINE_MODE }
requestOptions = dict({ TOKEN_SUPPRESS_GO_AHEAD:True, TOKEN_LINE_MODE:True })

class TelnetProtocol(object):

    def __init__(self):
        self.result = []

    def shift(self):
        if len(self.data) == 0:
            raise ValueError
        c = self.data[0]
        self.data = self.data[1:]
        return c

    def sendCommand(self, command):
        self.result.append(command)

    def getCommand(self):
        result = ''
        for cmds in self.result:
            if cmds[1] in [ TOKEN_WILL, TOKEN_WONT, TOKEN_DO, TOKEN_DONT ]:
                requestOptions.pop(cmds[2], None)
        for opt in requestOptions.keys():
            self.sendCommand([ TOKEN_IAC, TOKEN_WILL, opt ])
            requestOptions.pop(opt, None)
        for cmds in self.result:
            words = [ keyword[c] for c in cmds ]
            print 'TELNET SEND: {}'.format(' '.join(words))
            result += ''.join(cmds)
        return result

    def parse(self, data):
        self.data = data
        self.result = []
        while len(self.data) > 0:
            c = self.shift()
            if c != TOKEN_IAC:
                raise ValueError
            self.command()

    def command(self):
        c = self.shift()
        if c in [ TOKEN_WILL, TOKEN_WONT, TOKEN_DO, TOKEN_DONT ]:
            d = self.shift()
            self.accept(c, d)
        else:
            raise ValueError

    def accept(self, cmd, opt):
        print 'TELNET RECV: IAC {} {}'.format(keyword[cmd], keyword[opt])
        if cmd == TOKEN_WILL:
            if opt in acceptOptions:
                self.sendCommand([ TOKEN_IAC, TOKEN_DO, opt ])
            else:
                self.sendCommand([ TOKEN_IAC, TOKEN_DONT, opt ])
        elif cmd == TOKEN_DO:
            if opt in acceptOptions:
                self.sendCommand([ TOKEN_IAC, TOKEN_WILL, opt ])
            else:
                self.sendCommand([ TOKEN_IAC, TOKEN_WONT, opt ])
        elif cmd == TOKEN_WONT:
            self.sendCommand([ TOKEN_IAC, TOKEN_WONT, opt ])
        elif cmd == TOKEN_DONT:
            self.sendCommand([ TOKEN_IAC, TOKEN_DONT, opt ])
        else:
            raise ValueError

