import sys

class TerminalLogger(object):
    def __init__(self, stderr):
        self.stderr = stderr
    
    def info(self, message):
        self.stderr.write("INFO: {0}\r\n".format(message))
    
    def warn(self, message):
        self.stderr.write("WARN: {0}\r\n".format(message))
    
    def error(self, message):
        self.stderr.write("ERROR: {0}\r\n".format(message))

__logger = TerminalLogger(sys.stderr)

def set_logger(logger):
    global __logger
    __logger = logger

def info(fmt, *args):
    __logger.info(fmt % args)

def warn(fmt, *args):
    __logger.warn(fmt % args)

def error(fmt, *args):
    __logger.error(fmt % args)