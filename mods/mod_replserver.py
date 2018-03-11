from replserver.tcprepl import runReplServer
from replserver.logger import logger

def init():
    try:
        import threading
        logger.DEBUG = ${debug}
        logger.logInfo('{} {}'.format('${mod_id}', '${version}'))
        thread = threading.Thread(target=runReplServer, args=())
        thread.setDaemon(True)
        logger.logInfo('thread started..')
        thread.start()
    except:
        import traceback
        traceback.print_exc()
