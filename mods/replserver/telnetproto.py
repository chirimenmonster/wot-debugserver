import binascii
from logger import logger

TOKEN_SE    = 'SE'
TOKEN_GA    = 'GA'
TOKEN_SB    = 'SB'
TOKEN_WILL  = 'WILL'
TOKEN_WONT  = 'WONT'
TOKEN_DO    = 'DO'
TOKEN_DONT  = 'DONT'
TOKEN_IAC   = 'IAC'
TOKEN_IS    = 'IS'
TOKEN_SEND  = 'SEND'
TOKEN_INFO  = 'INFO'

TOKEN_ECHO              = 'echo'
TOKEN_SUPPRESS_GO_AHEAD = 'suppress-go-ahead'
TOKEN_TERMINAL_TYPE     = 'terminal-type'
TOKEN_WINDOW_SIZE       = 'window-size'
TOKEN_TERMINAL_SPEED    = 'terminal-speed'
TOKEN_FLOW_CONTROL      = 'remote-flow-control'
TOKEN_LINE_MODE         = 'line-mode'
TOKEN_ENVIRONMENT       = 'environment'
TOKEN_NEW_ENVIRON       = 'new-environment'

CODE_CMD = {
    # Negotiation Protocol
    TOKEN_SE:   b'\xf0',    # 240
    TOKEN_GA:   b'\xf9',    # 249
    TOKEN_SB:   b'\xfa',    # 250
    TOKEN_WILL: b'\xfb',    # 251
    TOKEN_WONT: b'\xfc',    # 252
    TOKEN_DO:   b'\xfd',    # 253
    TOKEN_DONT: b'\xfe',    # 254
    TOKEN_IAC:  b'\xff',    # 255

    # Sub-negotiation Command
    TOKEN_IS:   b'\x00',    # 0
    TOKEN_SEND: b'\x01',    # 1
    TOKEN_INFO: b'\x02',    # 2
}

CODE_OPT = {
    # Negotiation Options
    TOKEN_ECHO:                 b'\x01',    # 1
    TOKEN_SUPPRESS_GO_AHEAD:    b'\x03',    # 3
    TOKEN_TERMINAL_TYPE:        b'\x18',    # 24
    TOKEN_WINDOW_SIZE:          b'\x1f',    # 31
    TOKEN_TERMINAL_SPEED:       b'\x20',    # 32
    TOKEN_FLOW_CONTROL:         b'\x21',    # 33
    TOKEN_LINE_MODE:            b'\x22',    # 34
    TOKEN_ENVIRONMENT:          b'\x24',    # 36
    TOKEN_NEW_ENVIRON:          b'\x27',    # 39
}

CODE = {}
CODE.update(CODE_CMD)
CODE.update(CODE_OPT)

DICT_CMD = { v:k for k,v in CODE_CMD.items() }
DICT_OPT = { v:k for k,v in CODE_OPT.items() }

STATE_ACCEPT = 'ACCEPT'
STATE_REJECT = 'REJECT'
STATE_REQUEST = 'REQUEST'

acceptOptions = {
    'U':    [ TOKEN_SUPPRESS_GO_AHEAD, TOKEN_LINE_MODE ],
    'S':    [ TOKEN_LINE_MODE ],
}
requestOptions = {
    'U':    [ TOKEN_SUPPRESS_GO_AHEAD, TOKEN_TERMINAL_TYPE ],
    'S':    [],
}

class TelnetProtocol(object):

    def __init__(self):
        self.result = []
        self.state = { 'U': {}, 'S': {} }

    def shift(self):
        if len(self.data) == 0:
            raise ValueError
        c = self.data[0]
        self.data = self.data[1:]
        return c

    def shift_data(self):
        if len(self.data) == 0:
            raise ValueError
        i = self.data.find(TOKEN_IAC)
        result = self.data[:i-1]
        self.data = self.data[i-1:]
        return result

    def getState(self, category):
        if category == 'TERM':
            state = self.state['U'][TOKEN_TERMINAL_TYPE]
            if state == STATE_REJECT:
                return ''
            elif isinstance(state, dict):
                return state['value']
            return None
        else:
            raise ValueError

    def getCommandString(self, data):
        info = ' '.join([ token if token in CODE else '\'{}\''.format(token) for token in data ])
        result = ''.join([ CODE.get(token, token) for token in data ])
        return result, info           

    def parse(self, data):
        self.data = data
        self.recv = []
        while len(self.data) > 0:
            c = self.shift()
            if c != CODE[TOKEN_IAC]:
                raise ValueError
            self.command()
        return self.recv

    def command(self):
        c = self.shift()
        if c in DICT_CMD:
            d = self.shift()
            cmd = DICT_CMD[c]
            opt = DICT_OPT.get(d, '\\x' + binascii.b2a_hex(d))
            if cmd == TOKEN_SB:
                s = self.shift()
                subcmd = DICT_CMD.get(s, '\\x' + binascii.b2a_hex(s))
                if subcmd == TOKEN_IS:
                    arg = self.shift_data()
                    lastIac = DICT_CMD[self.shift()]
                    lastCmd = DICT_CMD[self.shift()]
                    self.recv.append([ TOKEN_IAC, cmd, opt, subcmd, arg, lastIac, lastCmd ])
            else:
                self.recv.append([ TOKEN_IAC, cmd, opt ])
        else:
            raise ValueError

    def negotiation(self, rcvddata):
        self.buffer = {}
        self.buffer['RECV'] = []
        if rcvddata is not None:
            self.buffer['RECV'] = self.parse(rcvddata)

        for msg in self.buffer['RECV']:
            data, info = self.getCommandString(msg)
            logger.logDebug('TELNET RCVD: {}'.format(info))
            cmd, opt = msg[1], msg[2]
            if cmd == TOKEN_WILL:
                if opt not in self.state['U']:
                    self.state['U'][opt] = TOKEN_WILL
                elif self.state['U'][opt] == TOKEN_DO:
                    self.state['U'][opt] = STATE_ACCEPT
            elif cmd == TOKEN_DO:
                if opt not in self.state['S']:
                    self.state['S'][opt] = TOKEN_DO
                elif self.state['S'][opt] == TOKEN_WILL:
                    self.state['S'][opt] = STATE_ACCEPT
            elif cmd == TOKEN_WONT:
                if self.state['S'][opt] == TOKEN_WONT:
                    self.state['S'][opt] = STATE_REJECT
                elif self.state['U'][opt] == TOKEN_DO:
                    self.state['U'][opt] = TOKEN_WONT
            elif cmd == TOKEN_DONT:
                if self.state['U'][opt] == TOKEN_DONT:
                    self.state['U'][opt] = STATE_REJECT
                elif self.state['S'][opt] == TOKEN_WILL:
                    self.state['S'][opt] = TOKEN_DONT
            elif cmd == TOKEN_SB:
                subcmd = msg[3]
                if subcmd == TOKEN_IS:
                    self.state['U'][opt] = { 'value': msg[4] }

        self.buffer['SEND'] = []
        if rcvddata is None:
            for opt in requestOptions['U']:
                self.state['U'][opt] = TOKEN_DO
                self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_DO, opt ])
            for opt in requestOptions['S']:
                self.state['S'][opt] = TOKEN_WILL
                self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_WILL, opt ])

        if self.state['U'][TOKEN_TERMINAL_TYPE] == STATE_ACCEPT:
            self.state['U'][TOKEN_TERMINAL_TYPE] = STATE_REQUEST
            self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_SB, TOKEN_TERMINAL_TYPE, TOKEN_SEND, TOKEN_IAC, TOKEN_SE ])
                
        for opt, state in self.state['U'].items():
            if state == TOKEN_WILL:
                if opt in acceptOptions['U']:
                    self.state['U'][opt] = STATE_ACCEPT
                    self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_DO, opt ])
                else:
                    self.state['U'][opt] = TOKEN_DONT
                    self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_DONT, opt ])
            elif state == TOKEN_WONT:
                self.sate['U'][opt] == STATE_REJECT
                self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_WONT, opt ])
        for opt, state in self.state['S'].items():
            if state == TOKEN_DO:
                if opt in acceptOptions['S']:
                    self.state['S'][opt] = STATE_ACCEPT
                    self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_WILL, opt ])
                else:
                    self.state['S'][opt] = TOKEN_WONT
                    self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_WONT, opt ])
            elif state == TOKEN_DONT:
                self.sate['S'][opt] == STATE_REJECT
                self.buffer['SEND'].append([ TOKEN_IAC, TOKEN_DONT, opt ])

        result = ''
        for cmd in self.buffer['SEND']:
            data, info = self.getCommandString(cmd)
            result += data
            logger.logDebug('TELNET SENT: {}, {}'.format(info, repr(data)))
        return result
