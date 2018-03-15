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
    'U':    [ TOKEN_SUPPRESS_GO_AHEAD, TOKEN_LINE_MODE, TOKEN_EXTEND_MSG ],
    'S':    [ TOKEN_LINE_MODE, TOKEN_NEW_ENVIRON ],
}
requestOptions = {
    'U':    [ TOKEN_SUPPRESS_GO_AHEAD, TOKEN_TERMINAL_TYPE, TOKEN_EXTEND_MSG ],
    'S':    [],
}
requestOptionsSubstate = {
    'U':    [ TOKEN_TERMINAL_TYPE ],
    'S':    [],
}

class TelnetProtocol(object):

    def __init__(self, handler=None):
        self.__state = { 'U': {}, 'S': {} }
        self.__extendMsgHandler = handler

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

    def __shift(self):
        if len(self.data) == 0:
            raise ValueError
        c = self.data[0]
        self.data = self.data[1:]
        return c

    def __shift_data(self):
        if len(self.data) == 0:
            raise ValueError
        i = self.data.find(CODE_CMD[TOKEN_IAC])
        result = self.data[:i]
        self.data = self.data[i:]
        return result

    def goahead(self):
        if self.__state['U'].get(TOKEN_SUPPRESS_GO_AHEAD, None) == STATE_ACCEPT:
            return None
        return CODE[TOKEN_IAC] + CODE[TOKEN_GA]

    def getState(self, category):
        if category == 'TERM':
            state = self.__state['U'][TOKEN_TERMINAL_TYPE]
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

    def __parse(self, data):
        self.data = data
        self.recv = []
        while len(self.data) > 0:
            c = self.__shift()
            if c != CODE[TOKEN_IAC]:
                raise ValueError
            self.__command()
        return self.recv

    def __command(self):
        c = self.__shift()
        if c in DICT_CMD:
            d = self.__shift()
            cmd = DICT_CMD[c]
            opt = DICT_OPT.get(d, '\\x' + binascii.b2a_hex(d))
            if cmd == TOKEN_SB:
                s = self.__shift()
                subcmd = DICT_CMD.get(s, '\\x' + binascii.b2a_hex(s))
                if subcmd == TOKEN_IS:
                    arg = self.__shift_data()
                    lastIac = DICT_CMD[self.__shift()]
                    lastCmd = DICT_CMD[self.__shift()]
                    self.recv.append([ TOKEN_IAC, cmd, opt, subcmd, arg, lastIac, lastCmd ])
            else:
                self.recv.append([ TOKEN_IAC, cmd, opt ])
        else:
            raise ValueError

    def control(self, rcvddata):
        if rcvddata:
            msgs = self.__parse(rcvddata)
        else:
            msgs = []
        for msg in msgs:
            data, info = self.getCommandString(msg)
            logger.logDebug('TELNET RCVD: {}'.format(info))

        msgs += [ [ None, None, opt ] for opt in requestOptions['U'] ]
        request = []
        for msg in msgs:
            cmd, opt = msg[1], msg[2]
            request.append(self.__getRequestRemoteState(cmd, opt))
            request.append(self.__getRequestLocalState(cmd, opt))
            request.append(self.__getRequestRemoteSubstate(msg))
        logger.logDebug('STATE: {}'.format(self.__state))

        request.append(self.__getRequestExtendMessage())        

        result = ''
        for msg in request:
            if msg is None:
                continue
            data, info = self.getCommandString(msg)
            result += data
            logger.logDebug('TELNET SENT: {}, {}'.format(info, repr(data)))
        return result


    def __getRequestRemoteState(self, cmd, opt):
        result = None
        state = self.__state['U'].get(opt, None)
        if state is None:
            if cmd is None:
                if opt in requestOptions['U']:
                    state = TOKEN_DO
                    result = [ TOKEN_IAC, TOKEN_DO, opt ]
            elif cmd == TOKEN_WILL:
                if opt in acceptOptions['U']:
                    state = TOKEN_DO
                    result = [ TOKEN_IAC, TOKEN_DO, opt ]
                else:
                    state = TOKEN_DONT
                    result = [ TOKEN_IAC, TOKEN_DONT, opt ]
        elif state == TOKEN_DO:
            if cmd == TOKEN_WILL:
                state = STATE_ACCEPT
            elif cmd == TOKEN_WONT:
                state = STATE_REJECT
                result = [ TOKEN_IAC, TOKEN_WONT, opt ]
        elif state == TOKEN_DONT:
            if cmd == TOKEN_DONT:
                state = STATE_REJECT
        self.__state['U'][opt] = state
        return result

    def __getRequestLocalState(self, cmd, opt):
        result = None
        state = self.__state['S'].get(opt, None)
        if state is None:
            if cmd is None:
                if opt in requestOptions['S']:
                    state = TOKEN_WILL
                    result = [ TOKEN_IAC, TOKEN_WILL, opt ]
            elif cmd == TOKEN_DO:
                if opt in acceptOptions['S']:
                    state = TOKEN_WILL
                    result = [ TOKEN_IAC, TOKEN_WILL, opt ]
                else:
                    state = TOKEN_WONT
                    result = [ TOKEN_IAC, TOKEN_WONT, opt ]
        elif state == TOKEN_WILL:
            if cmd == TOKEN_DO:
                state = STATE_ACCEPT
            elif cmd == TOKEN_DONT:
                state = TOKEN_REJECT
                result = [ TOKEN_IAC, TOKEN_DONT, opt ]
        elif state == TOKEN_WONT:
            if cmd == TOKEN_WONT:
                state = STATE_REJECT
        self.__state['S'][opt] = state
        return result

    def __getRequestRemoteSubstate(self, msg):
        result = None
        cmd, opt = msg[1], msg[2]
        state = self.__state['U'].get(opt, None)
        if state == STATE_ACCEPT:
            if opt in requestOptionsSubstate['U']:
                state = STATE_REQUEST
                result = [ TOKEN_IAC, TOKEN_SB, opt, TOKEN_SEND, TOKEN_IAC, TOKEN_SE ]
        elif state == STATE_REQUEST:
            if cmd == TOKEN_SB:
                subcmd = msg[3]
                if subcmd == TOKEN_IS:
                    value = msg[4]
                    state = { 'value': value }
                    logger.logDebug('TELNET SUB: {} = {}'.format(opt, value))
        self.__state['U'][opt] = state
        return result

    def __getRequestExtendMessage(self):
        if self.__extendMsgHandler is None:
            return None
        result = None
        opt = TOKEN_EXTEND_MSG
        state = self.__state['U'].get(opt, None)
        if isinstance(state, dict) and 'value' in state:
            result = self.__extendMsgHandler(state['value'])
            result = [ TOKEN_IAC, TOKEN_SB, TOKEN_EXTEND_MSG, TOKEN_IS, result, TOKEN_IAC, TOKEN_SE ]
        state = STATE_REQUEST
        self.__state['U'][opt] = state
        return result

