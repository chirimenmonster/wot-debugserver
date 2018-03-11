import datetime

class __Log(object):
    DEBUG = False

    def getTime(self):
        return datetime.time.strftime(datetime.datetime.now().time(), '%H:%M')

    def logInfo(self, text):
        print 'replserver %s: %s' % (self.getTime(), text)

    def logDebug(self, text):
        if self.DEBUG:
            print 'replserver %s: %s' % (self.getTime(), text)

try:
    import BigWorld
    class __Log(object):
        DEBUG = False
        
        def logInfo(self, text):
            BigWorld.logInfo('${mod_id}', text, None)
            
        def logDebug(self, text):
            if self.DEBUG:
                BigWorld.logDebug('${mod_id}', text, None)

    logger = __Log()

except ImportError:
    logger = __Log()
