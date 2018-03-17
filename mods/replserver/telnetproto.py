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

    EOF                 = 'EOF'
    SUSP                = 'SUSP'
    ABORT               = 'ABORT'
    EOR                 = 'EOR'

CODE_IAC = {
    TOKEN.IAC:  b'\xff',    # 255
}

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
    TOKEN.EOF:      b'\xec',    # 236
    TOKEN.SUSP:     b'\xed',    # 237
    TOKEN.ABORT:    b'\xee',    # 238
    TOKEN.EOR:      b'\xef',    # 239
}

CODE = {}
CODE.update(CODE_IAC)
CODE.update(CODE_CMD_SIMPLE)
CODE.update(CODE_CMD_NEGOTIATION)
CODE.update(CODE_OPT)
CODE.update(CODE_SLC)

DICT_CMD_SIMPLE = { v:k for k,v in CODE_CMD_SIMPLE.items() }
DICT_CMD_NEGO = { v:k for k,v in CODE_CMD_NEGOTIATION.items() if k in [ TOKEN.WILL, TOKEN.WONT, TOKEN.DO, TOKEN.DONT ] }
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
    'U':    [ TOKEN.SUPPRESS_GO_AHEAD, TOKEN.TERMINAL_TYPE ],
    'S':    [],
}
requestOptionsSubstate = {
    'U':    [ TOKEN.TERMINAL_TYPE, TOKEN.EXTEND_MSG ],
    'S':    [],
}

class _Command(object):

    def __init__(self, cmd, *opts, **kwargs):
        self.length = kwargs.get('length', None)
        self.opt = None
        self.subcmd = None
        self.arg = None
        self.__create(cmd, *opts)

    def __create(self, cmd, *opts):
        if cmd in [ TOKEN.WILL, TOKEN.WONT, TOKEN.DO, TOKEN.DONT ]:
            if len(opts) != 1:
                raise ValueError
            opt = opts[0]
            self.__cmd = [ TOKEN.IAC, cmd, opt ]
            self.cmd, self.opt = cmd, opt
        elif cmd in [ TOKEN.SB ]:
            if len(opts) < 2:
                raise ValueError
            opt, subcmd = opts[0], opts[1]
            if subcmd == TOKEN.SEND:
                self.__cmd = [ TOKEN.IAC, TOKEN.SB, opt, subcmd, TOKEN.IAC, TOKEN.SE ]
                self.cmd, self.opt, self.subcmd = cmd, opt, subcmd
            elif subcmd == TOKEN.IS:
                arg = opts[2]
                self.__cmd = [ TOKEN.IAC, TOKEN.SB, opt, subcmd, arg, TOKEN.IAC, TOKEN.SE ]
                self.cmd, self.opt, self.subcmd, self.arg = cmd, opt, subcmd, arg
        else:
            if len(opts) != 0:
                raise ValueError
            self.__cmd = [ TOKEN.IAC, cmd ]
            self.cmd = cmd

    @staticmethod
    def parse(data):
        #logger.logDebug('parse: {}'.format(repr(data)))
        try:
            if data[0] != CODE[TOKEN.IAC]:
                return None
            if data[1] in DICT_CMD_NEGO:
                cmd = DICT_CMD_NEGO[data[1]]
                opt = DICT_OPT.get(data[2], '\\x' + binascii.b2a_hex(data[2]))
                return _Command(cmd, opt, length=3)
            elif data[1] == CODE[TOKEN.SB]:
                i = data.find(CODE[TOKEN.IAC] + CODE[TOKEN.SE], 2)
                if i < 0:
                    raise IndexError
                opt = DICT_OPT.get(data[2], '\\x' + binascii.b2a_hex(data[2]))
                subcmd = DICT_CMD_NEGOTIATION.get(data[3], '\\x' + binascii.b2a_hex(data[3]))
                arg = data[4:i]
                return _Command(TOKEN.SB, opt, subcmd, arg, length=2+i+2)
            elif data[1] in DICT_CMD_SIMPLE:
                cmd = DICT_CMD_SIMPLE[data[1]]
                return _Command(cmd, length=2)
            elif data[1] in DICT_SLC:
                cmd = DICT_SLC[data[1]]
                return _Command(cmd, length=2)
            else:
                raise ValueError
        except IndexError:
            return None
 
    def code(self):
        result = ''.join([ CODE.get(token, token) for token in self.__cmd ])
        return result

    def info(self):
        result = ' '.join([ token if token in CODE else repr(token) for token in self.__cmd ])
        return result


class TelnetProtocol(object):

    def __init__(self, commandHandlers=None, optionHandlers=None):
        self.__state = { 'U': {}, 'S': {} }
        self.__commandHandler = commandHandlers
        self.__optionHandler = optionHandlers

    def goahead(self):
        if self.__state['U'].get(TOKEN.SUPPRESS_GO_AHEAD, None) == STATE.ACCEPT:
            return None
        return CODE[TOKEN.IAC] + CODE[TOKEN.GA]

    def setRequireOption(self, opt):
        self.__state['U'][opt] = STATE.REQUEST

    def getRequestExtendMsg(self, value):
        return _Command(TOKEN.SB, TOKEN.EXTEND_MSG, TOKEN.IS, value)

    def split(self, data):
        k = data.find('\n')
        if k < 0:
            k = None
        i = data.find(CODE[TOKEN.IAC], 0, k)
        code = _Command.parse(data[i:])
        if code is not None:
            data = data[:i] + data[i+code.length:]
        #logger.logDebug('split: {}, {}'.format(repr(data), code.info() if code else None))
        return data, code

    def control(self, msg):
        request = []
        if msg is None:
            for opt in requestOptions['U']:
                request.append(self.__getRequestRemoteState(None, opt))
                request.append(self.__getRequestLocalState(None, opt))
        else:
            logger.logDebug('TELNET RCVD: {}'.format(msg.info()))
            if self.__commandHandler and msg.cmd in self.__commandHandler:
                self.__commandHandler[msg.cmd]()
            request.append(self.__getRequestRemoteState(msg.cmd, msg.opt))
            request.append(self.__getRequestLocalState(msg.cmd, msg.opt))
            request.append(self.__getRequestRemoteSubstate(msg))
        logger.logDebug('STATE: {}'.format(self.__state))

        result = ''
        for msg in request:
            if msg is None:
                continue
            logger.logDebug('TELNET SENT: {}, {}'.format(msg.info(), repr(msg.code())))
            result += msg.code()
        return result


    def __getRequestRemoteState(self, cmd, opt):
        result = None
        state = self.__state['U'].get(opt, None)
        if state is None:
            if cmd is None:
                if opt in requestOptions['U']:
                    result =  _Command(TOKEN.DO, opt)
                    self.__state['U'][opt] = TOKEN.DO
                else:
                    return None
            elif cmd == TOKEN.WILL:
                if opt in acceptOptions['U']:
                    result = _Command(TOKEN.DO, opt)
                    self.__state['U'][opt] = STATE.ACCEPT
                else:
                    result = _Command(TOKEN.DONT, opt)
                    self.__state['U'][opt] = TOKEN.DONT
        elif state == TOKEN.DO:
            if cmd == TOKEN.WILL:
                self.__state['U'][opt] = STATE.ACCEPT
            elif cmd == TOKEN.WONT:
                result = _Command(TOKEN.WONT, opt)
                self.__state['U'][opt] = STATE.REJECT
        elif state == TOKEN.DONT:
            if cmd == TOKEN.DONT:
                self.__state['U'][opt] = STATE.REJECT
        return result

    def __getRequestLocalState(self, cmd, opt):
        result = None
        state = self.__state['S'].get(opt, None)
        if state is None:
            if cmd is None:
                if opt in requestOptions['S']:
                    result = _Command(TOKEN.WILL, opt)
                    self.__state['S'][opt] = TOKEN.WILL
            elif cmd == TOKEN.DO:
                if opt in acceptOptions['S']:
                    result = _Command(TOKEN.WILL, opt)
                    self.__state['S'][opt] = TOKEN.ACCEPT
                else:
                    result = _Command(TOKEN.WONT, opt)
                    self.__state['S'][opt] = TOKEN.WONT
        elif state == TOKEN.WILL:
            if cmd == TOKEN.DO:
                self.__state['S'][opt] = STATE.ACCEPT
            elif cmd == TOKEN.DONT:
                result = _Command(TOKEN.DONT, opt)
                self.__state['S'][opt] = TOKEN.REJECT
        elif state == TOKEN.WONT:
            if cmd == TOKEN.WONT:
                self.__state['S'][opt] = STATE.REJECT
        return result

    def __getRequestRemoteSubstate(self, msg):
        result = None
        cmd, opt, subcmd, arg = msg.cmd, msg.opt, msg.subcmd, msg.arg
        state = self.__state['U'].get(opt, None)
        if state == STATE.ACCEPT:
            if opt in requestOptionsSubstate['U']:
                self.__state['U'][opt] = STATE.REQUEST
                result = _Command(TOKEN.SB, opt, TOKEN.SEND)
        elif state == STATE.REQUEST:
            if cmd == TOKEN.SB and subcmd == TOKEN.IS:
                value = arg
                self.__state['U'][opt] = { 'value': value }
                logger.logDebug('TELNET SUB: {} = {}'.format(opt, value))
                if opt in self.__optionHandler:
                    result = self.__optionHandler[opt](value)
        return result
