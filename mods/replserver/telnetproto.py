import binascii
from logger import logger

class TOKEN:
    SE      = 'SE'
    NOP     = 'NOP'
    DM      = 'DM'
    BRK     = 'BRK'
    IP      = 'IP'
    AO      = 'AO'
    AYT     = 'AYT'
    EC      = 'EC'
    EL      = 'EL'
    GA      = 'GA'
    SB      = 'SB'
    WILL    = 'WILL'
    WONT    = 'WONT'
    DO      = 'DO'
    DONT    = 'DONT'
    IAC     = 'IAC'

    IS      = 'IS'
    SEND    = 'SEND'
    INFO    = 'INFO'

    ECHO                = 'echo'
    SUPPRESS_GO_AHEAD   = 'suppress-go-ahead'
    TERMINAL_TYPE       = 'terminal-type'
    WINDOW_SIZE         = 'window-size'
    TERMINAL_SPEED      = 'terminal-speed'
    FLOW_CONTROL        = 'remote-flow-control'
    LINE_MODE           = 'line-mode'
    ENVIRONMENT         = 'environment'
    NEW_ENVIRON         = 'new-environment'

    EXTEND_MSG          = 'extend-msg'

    SLC_EOF             = 'EOF'
    SLC_SUSP            = 'SUSP'
    SLC_ABORT           = 'ABORT'

CODE_CMD_SIMPLE = {
    TOKEN.NOP:  b'\xf1',    # 241
    TOKEN.DM:   b'\xf2',    # 242
    TOKEN.BRK:  b'\xf3',    # 243
    TOKEN.IP:   b'\xf4',    # 244
    TOKEN.AO:   b'\xf5',    # 245
    TOKEN.AYT:  b'\xf6',    # 246
    TOKEN.EC:   b'\xf7',    # 247
    TOKEN.EL:   b'\xf8',    # 248
    TOKEN.GA:   b'\xf9',    # 249
}

CODE_CMD_NEGOTIATION = {
    # Negotiation Protocol
    TOKEN.SE:   b'\xf0',    # 240
    TOKEN.SB:   b'\xfa',    # 250
    TOKEN.WILL: b'\xfb',    # 251
    TOKEN.WONT: b'\xfc',    # 252
    TOKEN.DO:   b'\xfd',    # 253
    TOKEN.DONT: b'\xfe',    # 254
    TOKEN.IAC:  b'\xff',    # 255

    # Sub-negotiation Command
    TOKEN.IS:   b'\x00',    # 0
    TOKEN.SEND: b'\x01',    # 1
    TOKEN.INFO: b'\x02',    # 2
}

CODE_OPT = {
    # Negotiation Options
    TOKEN.ECHO:                 b'\x01',    # 1
    TOKEN.SUPPRESS_GO_AHEAD:    b'\x03',    # 3
    TOKEN.TERMINAL_TYPE:        b'\x18',    # 24
    TOKEN.WINDOW_SIZE:          b'\x1f',    # 31
    TOKEN.TERMINAL_SPEED:       b'\x20',    # 32
    TOKEN.FLOW_CONTROL:         b'\x21',    # 33
    TOKEN.LINE_MODE:            b'\x22',    # 34
    TOKEN.ENVIRONMENT:          b'\x24',    # 36
    TOKEN.NEW_ENVIRON:          b'\x27',    # 39
    
    TOKEN.EXTEND_MSG:           b'\xfe',    # extention
}

CODE_SLC = {
    TOKEN.SLC_EOF:      b'\xec',    # 236
    TOKEN.SLC_SUSP:     b'\xed',    # 237
    TOKEN.SLC_ABORT:    b'\xee',    # 238
}

CODE = {}
CODE.update(CODE_CMD_SIMPLE)
CODE.update(CODE_CMD_NEGOTIATION)
CODE.update(CODE_OPT)
CODE.update(CODE_SLC)

DICT_CMD_SIMPLE = { v:k for k,v in CODE_CMD_SIMPLE.items() }
DICT_CMD_NEGOTIATION = { v:k for k,v in CODE_CMD_NEGOTIATION.items() }
DICT_OPT = { v:k for k,v in CODE_OPT.items() }
DICT_SLC = { v:k for k,v in CODE_SLC.items() }

class STATE:
    ACCEPT  = 'ACCEPT'
    REJECT  = 'REJECT'
    REQUEST = 'REQUEST'

acceptOptions = {
    'U':    [ TOKEN.SUPPRESS_GO_AHEAD, TOKEN.LINE_MODE, TOKEN.EXTEND_MSG ],
    'S':    [ TOKEN.LINE_MODE, TOKEN.NEW_ENVIRON ],
}
requestOptions = {
    'U':    [ TOKEN.SUPPRESS_GO_AHEAD, TOKEN.TERMINAL_TYPE, TOKEN.EXTEND_MSG ],
    'S':    [],
}
requestOptionsSubstate = {
    'U':    [ TOKEN.TERMINAL_TYPE, TOKEN.EXTEND_MSG ],
    'S':    [],
}

class TelnetProtocol(object):

    def __init__(self, handler=None):
        self.__state = { 'U': {}, 'S': {} }
        self.__optionHandler = handler

    def getCommandString(self, data):
        info = ' '.join([ token if token in CODE else repr(token) for token in data ])
        result = ''.join([ CODE.get(token, token) for token in data ])
        return result, info           

    def goahead(self):
        if self.__state['U'].get(TOKEN.SUPPRESS_GO_AHEAD, None) == STATE.ACCEPT:
            return None
        return CODE[TOKEN.IAC] + CODE[TOKEN.GA]

    def setRequireOption(self, opt):
        self.__state['U'][opt] = STATE.REQUEST

    def getRequestExtendMsg(self, value):
        return [ TOKEN.IAC, TOKEN.SB, TOKEN.EXTEND_MSG, TOKEN.IS, value, TOKEN.IAC, TOKEN.SE ]

    def split(self, data):
        k = data.find('\n')
        if k < 0:
            k = None
        i = data.find(CODE[TOKEN.IAC], 0, k)
        n = len(data)
        codes = result = None
        if i >= 0 and n > i + 1:
            c = data[i+1]
            if ord(c) > ord(CODE[TOKEN.SE]) and ord(c) < ord(CODE[TOKEN.SB]):
                codes = data[i:i+2]
                data = data[:i] + data[i+2:]
            elif c in DICT_SLC:
                codes = data[i:i+2]
                data = data[:i] + data[i+2:]
            elif c in [ CODE[TOKEN.WILL], CODE[TOKEN.WONT], CODE[TOKEN.DO], CODE[TOKEN.DONT] ]:
                if n > i + 2:
                    codes = data[i:i+3]
                    data = data[:i] + data[i+3:]
            elif c == CODE[TOKEN.SB]:
                j = data.find(CODE[TOKEN.IAC] + CODE[TOKEN.SE], i)
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
        i = self.data.find(CODE_CMD_NEGOTIATION[TOKEN.IAC])
        result = self.data[:i]
        self.data = self.data[i:]
        return result

    def __parse(self, data):
        self.data = data
        self.recv = []
        while len(self.data) > 0:
            c = self.__shift()
            if c != CODE[TOKEN.IAC]:
                raise ValueError
            self.__command()
        return self.recv

    def __command(self):
        c = self.__shift()
        if c in DICT_CMD_SIMPLE:
            pass
        elif c in DICT_CMD_NEGOTIATION:
            d = self.__shift()
            cmd = DICT_CMD_NEGOTIATION[c]
            opt = DICT_OPT.get(d, '\\x' + binascii.b2a_hex(d))
            if cmd == TOKEN.SB:
                s = self.__shift()
                subcmd = DICT_CMD_NEGOTIATION.get(s, '\\x' + binascii.b2a_hex(s))
                if subcmd == TOKEN.IS:
                    arg = self.__shift_data()
                    lastIac = DICT_CMD_NEGOTIATION[self.__shift()]
                    lastCmd = DICT_CMD_NEGOTIATION[self.__shift()]
                    self.recv.append([ TOKEN.IAC, cmd, opt, subcmd, arg, lastIac, lastCmd ])
            else:
                self.recv.append([ TOKEN.IAC, cmd, opt ])
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
                    state = TOKEN.DO
                    result = [ TOKEN.IAC, TOKEN.DO, opt ]
            elif cmd == TOKEN.WILL:
                if opt in acceptOptions['U']:
                    state = TOKEN.DO
                    result = [ TOKEN.IAC, TOKEN.DO, opt ]
                else:
                    state = TOKEN.DONT
                    result = [ TOKEN.IAC, TOKEN.DONT, opt ]
        elif state == TOKEN.DO:
            if cmd == TOKEN.WILL:
                state = STATE.ACCEPT
            elif cmd == TOKEN.WONT:
                state = STATE.REJECT
                result = [ TOKEN.IAC, TOKEN.WONT, opt ]
        elif state == TOKEN.DONT:
            if cmd == TOKEN.DONT:
                state = STATE.REJECT
        self.__state['U'][opt] = state
        return result

    def __getRequestLocalState(self, cmd, opt):
        result = None
        state = self.__state['S'].get(opt, None)
        if state is None:
            if cmd is None:
                if opt in requestOptions['S']:
                    state = TOKEN.WILL
                    result = [ TOKEN.IAC, TOKEN.WILL, opt ]
            elif cmd == TOKEN.DO:
                if opt in acceptOptions['S']:
                    state = TOKEN.WILL
                    result = [ TOKEN.IAC, TOKEN.WILL, opt ]
                else:
                    state = TOKEN.WONT
                    result = [ TOKEN.IAC, TOKEN.WONT, opt ]
        elif state == TOKEN.WILL:
            if cmd == TOKEN.DO:
                state = STATE.ACCEPT
            elif cmd == TOKEN.DONT:
                state = TOKEN.REJECT
                result = [ TOKEN.IAC, TOKEN.DONT, opt ]
        elif state == TOKEN.WONT:
            if cmd == TOKEN.WONT:
                state = STATE.REJECT
        self.__state['S'][opt] = state
        return result

    def __getRequestRemoteSubstate(self, msg):
        result = None
        cmd, opt = msg[1], msg[2]
        state = self.__state['U'].get(opt, None)
        if state == STATE.ACCEPT:
            if opt in requestOptionsSubstate['U']:
                self.__state['U'][opt] = STATE.REQUEST
                result = [ TOKEN.IAC, TOKEN.SB, opt, TOKEN.SEND, TOKEN.IAC, TOKEN.SE ]
        elif state == STATE.REQUEST:
            if cmd == TOKEN.SB and msg[3] == TOKEN.IS:
                value = msg[4]
                self.__state['U'][opt] = { 'value': value }
                logger.logDebug('TELNET SUB: {} = {}'.format(opt, value))
                if opt in self.__optionHandler:
                    result = self.__optionHandler[opt](value)
        return result
