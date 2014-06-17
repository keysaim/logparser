#*********************************************************************************************#
#*********************************************************************************************#
#******************witten by Neil Hao(nbaoping@cisco.com), 2013/05/19*************************#
#*********************************************************************************************#
#*********************************************************************************************#
#*********************************************************************************************#

from datetime import datetime
from datetime import timedelta
import os
import inspect
from  xml.dom import  minidom
import traceback
import logging

import recipe
from customer import *

NEW_VERSION = True

RES_DIR = 'output'

LOGGING_FORMAT = '%(asctime)s %(levelname)5s: %(filename)s:%(lineno)s[%(funcName)s]-> %(message)s'
__TIME_FMT = '%Y/%m/%d-%H:%M:%S'
__START_TIME = datetime( 1970, 1, 1 )

def init_logging( level=logging.INFO ):
	logging.basicConfig( level=level, format=LOGGING_FORMAT )

def is_new_version( ):
	return NEW_VERSION

def std_fmt_name( fmtName ):
	if fmtName.startswith( '$' ):
		nstr = fmtName[1:len(fmtName)]
		if nstr[0] == '-':
			nstr = nstr.replace( '-', '_' )
		fmtName = '_commonVal' + nstr
	return fmtName

def form_common_fmt_name( num ):
	nstr = str(num)
	if num < 0:
		nstr = nstr.replace( '-', '_' )
	fmtName = '_commonVal' + nstr
	return fmtName

def is_common_fmt_name( fmtName ):
	return fmtName.startswith( '_commonVal' )

def strptime( tstr, fmt ):
	if NEW_VERSION:
		return datetime.strptime( tstr, fmt )
	else:
		time = recipe.strptime( tstr, fmt )
		dtime = datetime( time[0], time[1], time[2], time[3], time[4], time[5] )
		return dtime

def total_seconds( dtime ):
	delta = dtime - __START_TIME
	if NEW_VERSION:
		return delta.total_seconds()
	else:
		return delta.seconds + delta.days*24*3600

def to_datetime( seconds ):
	return __START_TIME + timedelta( 0, seconds )

def delta_time( dtime1, dtime2 ):
	delta = dtime2 - dtime1
	return delta.total_seconds()

def str_time( dtime, fmt=__TIME_FMT ):
	return datetime.strftime( dtime, fmt )

def time_str( tstr, fmt=__TIME_FMT ):
	return strptime( tstr, fmt )

def seconds_str( tstr, fmt=__TIME_FMT ):
	dtime = strptime( tstr, fmt )
	return total_seconds( dtime )

def str_seconds( seconds, fmt=__TIME_FMT ):
	dtime = to_datetime( seconds )
	return str_time( dtime, fmt )

def cur_timestr( ):
	now = datetime.now()
	return str_time( now )

def mkdir( dname ):
	try:
		if not os.path.exists( dname ):
			os.makedirs( dname )
	except:
		logging.error( '\n'+traceback.format_exc() )
		logging.error( 'create directory:'+dname+' failed' )

def splitall(path):
	allparts = []
	while 1:
		parts = os.path.split(path)
		if parts[0] == path:  # sentinel for absolute paths
			allparts.insert(0, parts[0])
			break
		elif parts[1] == path: # sentinel for relative paths
			allparts.insert(0, parts[1])
			break
		else:
			path = parts[0]
			allparts.insert(0, parts[1])
	return allparts

def func_name():
	return inspect.stack()[1][3]

def raise_virtual( func ):
	raise Exception( 'derived must implement '+func+' virtual function' )

def has_attr(node, attrname):
	return node.hasAttribute( attrname )

def get_attrvalue(node, attrname):
     return node.getAttribute(attrname).encode('utf-8','ignore')

def get_nodevalue(node, index = 0):
    return node.childNodes[index].nodeValue.encode('utf-8','ignore')

def get_xmlnode(node, name):
    return node.getElementsByTagName(name)

class BaseObject( object ):
	def __init__( self ):
		pass

	def set_member( self, mname, value ):
		self.__dict__[mname] = value

	def get_member( self, mname ):
		return self.__dict__[mname]

	def exist( self, member ):
		return member in self.__dict__

	def exist_member( self, mname ):
		return mname in self.__dict__

	def copy_object( self, obj ):
		for mname in self.__dict__.keys():
			value = self.__dict__[mname]
			obj.set_member( mname, value )

	def __str__( self ):
		return str( self.__dict__ ) + '\t' + str( type(self) )

class InputArgs( BaseObject ):
	def __init__( self ):
		self.inputType = 'files'
		self.path = '%stdin%'
		self.type = 'translog'
		self.fmt = None
		self.configPath = None
		self.fieldParser = None
		self.customer = None
		self.sorted = False
		self.enableParallel = False
		self.numCores = -1
		self.mergeMode = False
		self.debugMode = 'info'

	def parse_argv( self, argv ):
		idx = 1
		size = len(argv)
		while idx < size:
			if idx >= size:
				logging.error( 'invalid input arguments' )
				self.__print_usage()
				return False
			arg = argv[ idx ]
			if arg == '-i':
				self.path = argv[ idx+1 ]
				idx += 2
			elif arg == '-x':
				self.configPath = argv[ idx+1 ]
				idx += 2
			elif arg == '-f':
				self.fmt = argv[ idx+1 ]
				idx += 2
			elif arg == '-t':
				self.type = argv[ idx+1 ]
				idx += 2
			elif arg == '-c':
				self.customer = argv[ idx+1 ]
				idx += 2
			elif arg == '-o':
				self.enableParallel = True
				idx += 1
			elif arg == '-p':
				self.numCores = int( argv[idx+1] )
				idx += 2
			elif arg == '-s':
				self.__parse_short_name_file( argv[idx+1] )
				idx += 2
			elif arg == '-m':
				self.mergeMode = True
				idx += 1
			elif arg == '-d':
				self.debugMode = argv[idx+1]
				idx += 2
			else:
				idx += 2

		self.__set_debug_mode( self.debugMode )
		if not self.path or not self.configPath:
			logging.error( 'invalid input arguments' )
			logging.info( '\tlogs path and config file must be setted\n' )
			self.__print_usage()
			return False
		if self.path == '%stdin%':
			logging.info( 'will read lines from the stdin' )
			self.path = './'
			self.inputType = 'stdin'

		if self.fmt is None and self.customer is not None:
			logging.info( 'format not set, use customer:'+str(self.customer)+' standard format' )
			self.fmt = get_log_fmt( self.customer )
		if self.fmt is not None:
			self.fmtType = self.fmt
			mdfmt = get_module_fmt( self.fmt, self.type )
			if mdfmt is not None:
				logging.info( 'using module format:'+mdfmt )
				self.fmt = mdfmt
				self.sorted = is_log_sorted(mdfmt)

		if self.numCores > 1:
			self.enableParallel = True

		return True

	def __set_debug_mode( self, mode ):
		level = logging.INFO
		if mode == 'debug':
			level = logging.DEBUG
		elif mode == 'info':
			level = logging.INFO
		elif mode == 'warn':
			level = logging.WARN
		elif mode == 'warning':
			level = logging.WARNING
		elif mode == 'error':
			level = logging.ERROR
		elif mode == 'critical':
			level = logging.CRITICAL
		
		print 'set debug mode:', mode, 'with level:', level
		init_logging( level )


	def __parse_short_name_file( self, ipath ):
		fin = open( ipath, 'r' )
		for line in fin:
			line = line.strip()
			if len(line) == 0 or line.startswith( '#' ):
				continue

			segs = line.split( '=' )
			shortName = segs[0].strip()
			fmt = segs[1].strip()
			if len(shortName) > 0 and len(fmt) > 0:
				register_log_fmt( shortName, fmt )
			else:
				logging.error( 'wrong shortName line:'+line )
						
	def __print_usage( self ):
		print 'Usage:'
		print '\tmain.py -i <logs path> -x <config file> [ -t <log type>  -f <log format> ]'

