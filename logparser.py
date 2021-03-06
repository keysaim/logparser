#*********************************************************************************************#
#*********************************************************************************************#
#******************witten by Neil Hao(nbaoping@cisco.com), 2013/05/19*************************#
#*********************************************************************************************#
#*********************************************************************************************#
#*********************************************************************************************#
import logging

from datetime import datetime
from base import *
from filter import *

def standard_translog( line ):
	isInField = False
	idx = 0
	nidx = line.find( '"' )
	if nidx < 0:
		return line

	nline = ''
	while nidx >= 0:
		if isInField:
			segStr = line[idx:nidx]
			nstr = segStr.replace( ' ', '|' )
			isInField = False
		else:
			isInField = True
			nstr = line[idx:nidx]
		nline += nstr

		idx = nidx + 1 #skip the '"'
		nidx = line.find( '"', idx )
	
	nstr = line[idx:len(line)]
	nline += nstr
	return nline


class LogParser( object ):
	def __init__( self ):
		pass

	def parse_line( self, line ):
		raise Exception( 'derived class must implement function parse_line' )

class LogInfo( object ):
	def __init__( self ):
		self.servTime = 0
		self.recvdTime = 0
		self._commonIndex = 0
	
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
		return str( self.__dict__ )


#======================================================================
#================implement parser for web-engine translog==============
#======================================================================
WE_XACTLOG_APACHE_STR = "%a %u %O %b %I %m %>s %t %D"
WE_XACTLOG_EXT_SQUID_STR = "%Z %D %a %R/%>s %O %m %u %M"


class WELogInfo( LogInfo ):
	def __init__( self ):
		super(WELogInfo, self).__init__()
	
	def setCip( self, ip ):
		self.cip = ip

	def setUri( self, uri ):
		self.uri = uri

	def setMethod( self, method ):
		self.method = method

	def setRtime( self, rtime ):
		self.rtime = rtime

	def setRtimeT( self, rtime ):
		self.rtime = rtime

	def setSent( self, sent ):
		self.sent = sent

	def setAllSent( self, sent ):
		self.allSent = sent

	def setStime( self, stime ):
		self.stime = stime			#in microsecond

	def setStatus( self, status ):
		self.status = status
	
	def setRequestDes( self, des ):
		self.requestDes = des

	def setMimeType( self, mimeType ):
		self.mimeType = mimeType

	def setDummy( self, dummy ):
		pass

	def exist( self, member ):
		return member in self.__dict__

	def __str__( self ):
		return str(self.__dict__)

#private global variables
__weStrFmtSet = ['%b', '%D', '%I', ]
__weIntFmtSet = ['%a', '%A', '%h', '%H', 'm']

__fmtNameMap = {
	'%a' : 'clientIp',
	'%A' : 'seIp',
	'%b' : 'bytesSent',
	'%B' : 'bitrate',
	'%C' : 'lookupTime',
	'%D' : 'servTime',
	'%E' : 'encType',
	'%g' : 'storageUrl',
	'%G' : 'sourceUrl',
	'%h' : 'remoteHost',
	'%H' : 'protocol',
	'%i' : 'sessionId',
	'%I' : 'bytesRecvd',
	'%k' : 'trackMethod',
	'%m' : 'method',
	'%M' : 'mimeType',
	'%O' : 'bytesSentAll',
	'%q' : 'queryString',
	'%r' : 'firstLine',
	'%R' : 'description',
	'%>s' : 'status',
	'%S' : 'sessionStatus',
	'%t' : 'standardTime',
	'%T' : 'servSeconds',
	'%u' : 'urlAll',
	'%U' : 'url',
	'%V' : 'hostHeader',
	'%y' : 'abrType',
	'%X' : 'connStatus',
	'%Z' : 'recvdTime'
}

__nameFmtMap = {
	'clientIp'		: '%a',
	'seIp'			: '%A',
	'bytesSent'		: '%b',
	'bitrate'		: '%B',
	'lookupTime'	: '%C',
	'servTime'		: '%D',
	'encType'		: '%E',
	'storageUrl'	: '%g',
	'sourceUrl'		: '%G',
	'remoteHost'	: '%h',
	'protocol'		: '%H',
	'sessionId'		: '%i',
	'bytesRecvd'	: '%I',
	'trackMethod'	: '%k',
	'method'		: '%m',
	'mimeType'		: '%M',
	'bytesSentAll'	: '%O',
	'queryString'	: '%q',
	'firstLine'		: '%r',
	'description'	: '%R',
	'status'		: '%>s',
	'sessionStatus'	: '%S',
	'standardTime'	: '%t',
	'servSeconds'	: '%T',
	'urlAll'		: '%u',
	'url'			: '%U',
	'hostHeader'	: '%V',
	'abrType'		: '%y',
	'connStatus'	: '%X',
	'recvdTime'		: '%Z'
}

def get_fmt_by_name( name ):
	if name in __nameFmtMap:
		return __nameFmtMap[name]
	return None

def get_name_by_fmt( fmt ):
	if fmt in __fmtNameMap:
		return __fmtNameMap[fmt]
	return None

def std_common_value( fmt, value ):
	vtype = fmt[2:len(vtype)]
	if vtype == 'f':
		value = float(value)
	elif vtype == 'i':
		value = int(value)
	return value

def set_log_info( logInfo, fmt, value ):
	if fmt.startswith('%$'):
		logInfo._commonIndex += 1
		name = form_common_fmt_name( logInfo._commonIndex )
	else:
		name = get_name_by_fmt( fmt )
	if name is None:
		return
	logInfo.set_member( name, value )


#implement parser for extsqu format

class IFieldParser( object ):
	def __init__( self ):
		pass

	def parse_field( self, logInfo, field, fmt ):
		raise Exception( 'derived class must implement function parse_field' )


def __parse_string( field ):
	return field

def __parse_integer( field ):
	return int(field)

class WELogParser( LogParser ):
	fmtmap = None

	def __init_parser( self ):
		pass

	def __init__( self, fmt = None, fieldParser = None, fmtType = 'common' ):
		if WELogParser.fmtmap is None:
			self.__init_parser()
		self.__parsefuncs = None
		self.timeFmt = '[%d/%b/%Y:%H:%M:%S'
		self.__fieldParser = fieldParser
		self.fmtType = fmtType
		if fmt is not None:
			self.init_format( fmt )

	def init_format( self, fmt ):
		self.__parsefuncs = list()
		fmt = fmt.strip()
		segs = fmt.split()
		for token in segs:
			pfuncs = (WELogParser.parseOthers, WELogInfo.setDummy, token, self )
			if token in WELogParser.fmtmap:
				pfuncs = WELogParser.fmtmap[token]
				obj = self
				if len(pfuncs) > 2:
					obj = pfuncs[2]
				pfuncs = (pfuncs[0], pfuncs[1], token, obj )
			self.__parsefuncs.append( pfuncs )

	def parse_line( self, line ):
		if self.__parsefuncs is None:
			logging.error( 'fatal error, format not setted' )
			return None
		line = standard_translog( line )
		fields = None
		if self.fmtType.startswith( 'fms' ):
			if line.startswith( 's-ip' ):
				return None
			line = line.replace( '|', '\t', 1 )
			fields = line.split( '\t' )
		elif self.fmtType.startswith( 'we_' ):
			line = line.replace( '\t', ' ' )
			fields = line.split( ' ' )
		else:
			fields = line.split( ' ' )
		if len(fields) < len(self.__parsefuncs):
			logging.debug( 'invalid line:'+line )
			#append '-' for the old version
			rest = len(self.__parsefuncs) - len(fields)
			count = 0
			while count < rest:
				fields.append( '-' )
				count += 1
		logInfo = LogInfo()
		logInfo.originLine = line
		i = 0
		for funcs in self.__parsefuncs:
			value = funcs[0]( funcs[3], fields[i], logInfo, funcs[2] )
			if value is None:
				logging.debug( 'parse line failed:'+line )
				return None
			set_log_info( logInfo, funcs[2], value )
			i += 1

		return logInfo

	def parseString( self, field, logInfo, fmt ):
		return field

	def parseInt( self, field, logInfo, fmt ):
		try:
			value = int( field )
			return value
		except:
			logging.debug( 'not a integer string:'+field+',fmt:'+fmt )
			return None

	def parseFloat( self, field, logInfo, fmt ):
		try:
			value = float( field )
			return value
		except:
			logging.debug( 'not a float string'+field+',fmt:'+fmt )
			return None

	def parseStandardTime( self, field, logInfo, fmt ):
		idx = field.rfind( '+' )
		tstr = field[ 0:idx ]
		timeFmt = '[%d/%b/%Y:%H:%M:%S'
		dtime = strptime( tstr, timeFmt )
		dtime = total_seconds( dtime )
		return dtime

	#[21/Apr/2013:00:54:59.848+0000]
	#%d/%b/%Y:%H:%M:%S.%f
	def parseRecvdTime( self, field, logInfo, fmt ):
		segs = field.split( '.' )
		dtime = strptime( segs[0], self.timeFmt )
		dtime = total_seconds( dtime )
		mstr = segs[1]
		nsegs = mstr.split( '+' )
		if len(nsegs) < 2:
			nsegs = mstr.split( '-' )
		if len(nsegs) >= 2:
			msec = float( nsegs[0] )
			dtime += (msec/1000.0)
		return dtime

	def parseOthers( self, field, logInfo, fmt ):
		ret = False
		if fmt[0] == '%':
			ret = self.__parse_combined( field, logInfo, fmt )
		if not ret and self.__fieldParser:
			ret = self.__fieldParser.parse_field( logInfo, field, fmt )
		return ret

	def __parse_combined( self, field, logInfo, fmt ):
		fmtList = self.__split_fmt( fmt )
		fieldList = self.__split_fields( field, fmtList )
		ret = False
		for item in fieldList:
			if item[0] in WELogParser.fmtmap:
				funcs = WELogParser.fmtmap[ item[0] ]
				value = funcs[0]( self, item[1], logInfo, item[0] )
				set_log_info( logInfo, item[0], value )
				ret = True
			else:
				if self.__fieldParser is not None:
					self.__fieldParser.parse_field( logInfo, item[1], item[0] )
		return ret


	def __split_fmt( self, fmt ):
		idx = 0
		fmtList = list()
		size = len(fmt)
		while idx < size:
			off = 2
			if fmt[idx] == '%':
				if idx+1 >= size:
					break
				item = None
				if fmt[idx+1] == '>':
					if idx+2 >= size:
						break
					item = fmt[idx:idx+3]
					off = 3
				else:
					item = fmt[idx:idx+2]
				if item:
					fmtList.append( item )
			else:
				logging.error( 'error char:'+fmt[idx] )
				break
			nidx = fmt.find( '%', idx+off )
			if nidx == -1:
				item = fmt[idx+off:size]
				if len(item) > 0:
					fmtList.append( item )
				break
			item = fmt[idx+off:nidx]
			fmtList.append( item )
			idx = nidx
		return fmtList

	def __split_fields( self, field, fmtList ):
		idx = 1
		fsize = len(fmtList)
		fidx = 0
		fieldList = list()
		while idx < fsize:
			nidx = field.find( fmtList[idx], fidx )
			if nidx < 0:
				break
			fmt = fmtList[idx-1]
			item = field[ fidx:nidx ]
			fieldList.append( (fmt, item) )
			fidx = nidx + len(fmtList[idx])		#skip the split string
			idx += 2
		fieldSize = len(field)
		if fidx < fieldSize:
			item = field[ fidx:fieldSize]
			fmt = fmtList[ idx-1 ]
			fieldList.append( (fmt, item) )
		return fieldList


	def parseDummy( self, field, logInfo, set_func, fmt ):
		return True


WELogParser.fmtmap = {
			'%$':(WELogParser.parseString, WELogInfo.setDummy),# WELogInfo.setCip),
			'%$i':(WELogParser.parseInt, WELogInfo.setDummy),# WELogInfo.setCip),
			'%$f':(WELogParser.parseFloat, WELogInfo.setDummy),# WELogInfo.setCip),
			'%a':(WELogParser.parseString, WELogInfo.setDummy),# WELogInfo.setCip),
			'%A':(WELogParser.parseString, WELogInfo.setDummy),
			'%b':(WELogParser.parseInt, WELogInfo.setDummy),# WELogInfo.setSent),
			'%B':(WELogParser.parseInt, WELogInfo.setDummy),# WELogInfo.setSent),
			'%C':(WELogParser.parseString, WELogInfo.setDummy),
			'%D':(WELogParser.parseInt, WELogInfo.setDummy),# WELogInfo.setStime),
			'%E':(WELogParser.parseString, WELogInfo.setDummy),
			'%g':(WELogParser.parseString, WELogInfo.setDummy),
			'%G':(WELogParser.parseString, WELogInfo.setDummy),
			'%h':(WELogParser.parseString, WELogInfo.setDummy),
			'%H':(WELogParser.parseString, WELogInfo.setDummy),
			'%i':(WELogParser.parseString, WELogInfo.setDummy),
			'%I':(WELogParser.parseInt, WELogInfo.setDummy),
			'%k':(WELogParser.parseString, WELogInfo.setDummy),
			'%m':(WELogParser.parseString, WELogInfo.setDummy),# WELogInfo.setMethod),
			'%M':(WELogParser.parseString, WELogInfo.setDummy),# WELogInfo.setMimeType),
			'%O':(WELogParser.parseInt, WELogInfo.setDummy),# WELogInfo.setAllSent),
			'%q':(WELogParser.parseString, WELogInfo.setDummy),
			'%r':(WELogParser.parseString, WELogInfo.setDummy),
			'%R':(WELogParser.parseString, WELogInfo.setDummy),# WELogInfo.setRequestDes),
			'%>s':(WELogParser.parseInt, WELogInfo.setDummy),# WELogInfo.setStatus),
			'%S':(WELogParser.parseString, WELogInfo.setDummy),
			'%t':(WELogParser.parseStandardTime, WELogInfo.setDummy),# WELogInfo.setRtimeT),
			'%T':(WELogParser.parseFloat, WELogInfo.setDummy),
			'%u':(WELogParser.parseString, WELogInfo.setDummy),#WELogInfo.setUri),
			'%U':(WELogParser.parseString, WELogInfo.setDummy),
			'%V':(WELogParser.parseString, WELogInfo.setDummy),
			'%y':(WELogParser.parseString, WELogInfo.setDummy),
			'%X':(WELogParser.parseString, WELogInfo.setDummy),
			'%Z':(WELogParser.parseRecvdTime, WELogInfo.setDummy)# WELogInfo.setRtime)
			}

def register_token( token, fmtName, parse_func, obj, fmtType='string' ):
	WELogParser.fmtmap[token] = (parse_func, None, obj)
	__fmtNameMap[token] = fmtName
	__nameFmtMap[fmtName] = token
	register_filter( fmtName, fmtType )
