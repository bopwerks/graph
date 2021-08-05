import sys

class TerminalLogger(object):
    def __init__(self, stderr):
        self.stderr = stderr
    
    def error(self, message):
        self.stderr.write("ERROR: {0}\r\n".format(message))
    
    def warn(self, message):
        self.stderr.write("WARN: {0}\r\n".format(message))
    
    def info(self, message):
        self.stderr.write("INFO: {0}\r\n".format(message))
    
    def debug(self, message):
        self.stderr.write("DEBUG: {0}\r\n".format(message))

__logger = TerminalLogger(sys.stderr)

def set_logger(logger):
    global __logger
    __logger = logger

class Level(object):
    ERROR = 0
    WARN  = 1
    INFO  = 2
    DEBUG = 3

__log_level = Level.INFO
def set_log_level(level):
    global __log_level
    __log_level = level

def error(fmt, *args):
    if __log_level >= Level.ERROR:
        __logger.error(fmt % args)

def warn(fmt, *args):
    if __log_level >= Level.WARN:
        __logger.warn(fmt % args)

def info(fmt, *args):
    if __log_level >= Level.INFO:
        __logger.info(fmt % args)

def debug(fmt, *args):
    if __log_level >= Level.DEBUG:
        __logger.debug(fmt % args)
