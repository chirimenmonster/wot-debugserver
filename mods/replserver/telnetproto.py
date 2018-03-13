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

TOKEN_EXTEND_MSG        = 'extend-msg'

TOKEN_SLC_EOF       = 'EOF'
TOKEN_SLC_SUSP      = 'SUSP'
TOKEN_SLC_ABORT     = 'ABORT'


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
    
    TOKEN_EXTEND_MSG:           b'\xfe',    # extention
}

CODE_SLC = {
    TOKEN_SLC_EOF:      b'\xec',    # 236
    TOKEN_SLC_SUSP:     b'\xed',    # 237
    TOKEN_SLC_ABORT:    b'\xee',    # 238
}

CODE = {}
CODE.update(CODE_CMD)
CODE.update(CODE_OPT)
CODE.update(CODE_SLC)

DICT_CMD = { v:k for k,v in CODE_CMD.items() }
DICT_OPT = { v:k for k,v in CODE_OPT.items() }
DICT_SLC = { v:k for k,v in CODE_SLC.items() }

STATE_ACCEPT = 'ACCEPT'
STATE_REJECT = 'REJECT'
STATE_REQUEST = 'REQUEST'

acceptOptions = {
    'U':    [ TOKEN_SUPPRESS_GO_AHEAD, TOKEN_LINE_MODE ],
    'S':    [ TOKEN_LINE_MODE, TOKEN_NEW_ENVIRON ],
}
requestOptions = {
    'U':    [ TOKEN_SUPPRESS_GO_AHEAD, TOKEN_TERMINAL_TYPE ],
    'S':    [],
}

class TelnetProtocol(object):

    def __init__(self, handler=None):
        self.result = []
        self.state = { 'U': {}, 'S': {} }
        self.extendMsgHandler = handler

    def split(self, data):
        k = data.find('\n')
        if k < 0:
            k = None
        i = data.find(CODE[TOKEN_IAC], 0, k)
        n = len(data)
        codes = result = None
        if i >= 0 and n > i + 1:
            c = data[i+1]
            if ord(c) > ord(CODE[TOKEN_SE]) and ord < ord(CODE[TOKEN_SB]):
                codes = data[i:i+2]
                data = data[:i] + data[i+2:]
            elif c in DICT_SLC:
                codes = data[i:i+2]
                data = data[:i] + data[i+2:]
            elif c in [ CODE[TOKEN_WILL], CODE[TOKEN_WONT], CODE[TOKEN_DO], CODE[TOKEN_DONT] ]:
                if n > i + 2:
                    codes = data[i:i+3]
                    data = data[:i] + data[i+3:]
            elif c == CODE[TOKEN_SB]:
                j = data.find(CODE[TOKEN_IAC] + CODE[TOKEN_SE], i)
                if j > 0:
                    codes = data[i:j+2]
                    data = data[:i] + data[j+2:]
            else:
                raise ValueError
        return data, codes

    def shift(self):
        if len(self.data) == 0:
            raise ValueError
        c = self.data[0]
        self.data = self.data[1:]
        return c

    def shift_data(self):
        if len(self.data) == 0:
            raise ValueError
        i = self.data.find(CODE_CMD[TOKEN_IAC])
        result = self.data[:i]
        self.data = self.data[i:]
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
        info = ' '.join([ token if token in CODE else repr(token) for token in data ])
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
        request = []

        if rcvddata:
            for msg in self.parse(rcvddata):
                self.__acceptReceivedMessage(msg)
        else:
            request.extend(self.__pushRequestMessage())
            
        request.extend(self.__pushRequireTermMessage())
        request.extend(self.__pushReplyMessage())
        request.extend(self.__processExtendMessage())

        result = ''
        for cmd in request:
            data, info = self.getCommandString(cmd)
            result += data
            logger.logDebug('TELNET SENT: {}, {}'.format(info, repr(data)))
        return result

    def __acceptReceivedMessage(self, msg):
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
                logger.logDebug('TELNET SUB: {} = {}'.format(opt, msg[4]))

    def __pushRequestMessage(self):
        request = []
        for opt in requestOptions['U']:
            self.state['U'][opt] = TOKEN_DO
            request.append([ TOKEN_IAC, TOKEN_DO, opt ])
        for opt in requestOptions['S']:
            self.state['S'][opt] = TOKEN_WILL
            request.append([ TOKEN_IAC, TOKEN_WILL, opt ])
        return request
    
    def __pushReplyMessage(self):
        request = []
        for opt, state in self.state['U'].items():
            if state == TOKEN_WILL:
                if opt in acceptOptions['U']:
                    self.state['U'][opt] = STATE_ACCEPT
                    request.append([ TOKEN_IAC, TOKEN_DO, opt ])
                else:
                    self.state['U'][opt] = TOKEN_DONT
                    request.append([ TOKEN_IAC, TOKEN_DONT, opt ])
            elif state == TOKEN_WONT:
                self.sate['U'][opt] == STATE_REJECT
                request.append([ TOKEN_IAC, TOKEN_WONT, opt ])
        for opt, state in self.state['S'].items():
            if state == TOKEN_DO:
                if opt in acceptOptions['S']:
                    self.state['S'][opt] = STATE_ACCEPT
                    request.append([ TOKEN_IAC, TOKEN_WILL, opt ])
                else:
                    self.state['S'][opt] = TOKEN_WONT
                    request.append([ TOKEN_IAC, TOKEN_WONT, opt ])
            elif state == TOKEN_DONT:
                self.sate['S'][opt] == STATE_REJECT
                request.append([ TOKEN_IAC, TOKEN_DONT, opt ])
        return request

    def __pushRequireTermMessage(self):
        request = []
        if self.state['U'][TOKEN_TERMINAL_TYPE] == STATE_ACCEPT:
            self.state['U'][TOKEN_TERMINAL_TYPE] = STATE_REQUEST
            request.append([ TOKEN_IAC, TOKEN_SB, TOKEN_TERMINAL_TYPE, TOKEN_SEND, TOKEN_IAC, TOKEN_SE ])
        return request

    def __processExtendMessage(self):
        request = []
        query = self.state['U'].get(TOKEN_EXTEND_MSG, None)
        if query and query['value'] and self.extendMsgHandler is not None:
            result = self.extendMsgHandler(query['value'])
            request.append([ TOKEN_IAC, TOKEN_SB, TOKEN_EXTEND_MSG, TOKEN_IS, result, TOKEN_IAC, TOKEN_SE ])
            query['value'] = None
        return request
