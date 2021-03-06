try:
	import multiprocessing
except:
	pass

import time
import os
import sys
import logging

from base import *
from factory import *
from anlyhandler import *
from logparser import *
from regexformat import *
from errorlog import *

def create_parser_from_type( args ):
	parser = None
	logType = args.type
	fmt = args.fmt
	if logType == 'translog':
		parser = WELogParser( fmt, args.fieldParser, args.fmtType )
	elif logType == 'errorlog':
		parser = ErrorlogParser()
	elif logType == 'regex':
		parser = RegexParser(fmt)
	elif logType == 'regex_split':
		parser = RegexParser(fmt, 'split')
	elif logType == 'regex_find':
		parser = RegexParser(fmt, 'find')
	
	if parser != None:
		parser.formatter = args.formatter
	return parser



class InputFile( BaseObject ):
	def __init__( self, startTime, path, offset, endOffset = -1 ):
		self.startTime = startTime
		self.path = path
		self.offset = offset
		self.endOffset = endOffset

class InputTask( BaseObject ):
	def __init__( self, inputList, startTime, endTime ):
		self.inputList = inputList
		self.startTime = startTime
		self.endTime = endTime
		self.startBufTime = 0

class OutputFile( BaseObject ):
	def __init__( self, outPath, errPath ):
		self.outPath = outPath
		self.errPath = errPath
		self.headOffset = -1
		self.tailOffset = 0
		self.fileStartTime = -1
		self.fileEndTime = -1



class AnlyWorker( object ):
	def __init__( self, tid, task, args ):
		super(AnlyWorker, self).__init__()
		self.tid = tid
		self.task = task
		self.args = args

	def run( self ):
		logging.info( '=====================process '+str(self.tid)+' started========================' )
		stime = time.time()
		(totalLineCount, ofileList) = self.do_task( self.tid, self.task, self.args )
		spent = time.time() - stime
		logging.info( 'process:'+str(self.tid)+\
				' exit parsed total lines:'+str(totalLineCount)+' in '+str(spent)+' seconds' )
		return (totalLineCount, ofileList)


	def do_task( self, tid, task, args ):
		logging.info( '%%%%%%%%%%%%%%%%%%%%%%%%%%% '+str(tid)+',args:'+str(args) )
	
		anlyFactory = AnalyserFactory( args.curTimeStr )
		anlyList = anlyFactory.create_from_args( args, task.startTime, task.endTime )
		self.anlyList = anlyList
		parser = create_parser_from_type( args )
		self.parser = parser
	
		self.update_anlylist_info( tid, task, anlyList )

		totalLineCount = 0
		#parse all the files
		for ifile in task.inputList:
			startTime = time.time()
			lineCount = self.anly_file( tid, ifile )
			totalLineCount += lineCount
			elapsed = time.time() - startTime
			logging.info( '==============================='+'tid:'+str(tid)+\
					',elapsed:'+str(elapsed * 1000)+'ms,'+str(lineCount)+' lines in '+ifile.path )
	
		outputList = list()
		for anly in anlyList:
			ofile = OutputFile( anly.outPath, anly.errPath )
			outputList.append( ofile )
			anly.close()
			#must assign after anly closed, since the file flush happens in the closing
			ofile.fileStartTime = anly.fileStartTime
			ofile.fileEndTime = anly.fileEndTime
	
		return (totalLineCount, outputList)

	def update_anlylist_info( self, tid, task, anlyList ):
		stime = int(task.startTime)
		etime = int(task.endTime)
		for anly in anlyList:
			anly.set_one_process_mode( 0 )
			anly.tid = tid
			anly.startBufTime = task.startBufTime
			pace = anly.pace

			#for the tasks, must abey to the startTime setting in the config files
			#so, no need to adjust the startTime end endTime

			#open the output file
			dirName = os.path.dirname( anly.outPath )
			odir = 'tmp'
			dirName = os.path.join( dirName, 'tmp' )
			mkdir( dirName )
			baseName = os.path.basename( anly.outPath ) + '.' + str(tid)
			anly.outPath = os.path.join( dirName, baseName )
			anly.open_output_files()
			logging.debug( 'tid:'+str(tid)+',anly:'+str(anly) )
	
	def __parse_line( self, line ):
		try:
			parser = self.parser
			logInfo = parser.parse_line( line )
			logging.debug( 'parsed info:'+str(logInfo) )
			if parser.formatter is not None:
				logInfo = parser.formatter.fmt_log( logInfo )
				logging.debug( 'formatted info:'+str(logInfo) )
			return logInfo
		except:
			logging.debug( '\n'+traceback.format_exc() )
	
		return None
	
	def __parse_log( self, line ):
		logInfo = self.__parse_line( line )
		if logInfo is None:
			return False
		for anly in self.anlyList:
			anly.analyse_log( logInfo )
	
		return True
	
	def anly_file( self, tid, ifile):
		logging.debug( 'tid:'+str(tid)+'ifile:'+str(ifile) )
		path = ifile.path
		offset = ifile.offset
		endOffset = ifile.endOffset
	
		fin = open( path, 'r' )
		curPos = 0
		if offset > 0:
			fin.seek( offset, 0 )
			curPos = offset
		lineCount = 0
		lastTime = time.time()
		for line in fin:
			if endOffset >= 0:
				if curPos >= endOffset:
					break
			lineCount += 1
			curPos += len(line)
			line = line.strip()
			if line.startswith( '#' ):
				continue
			self.__parse_log( line )
			if (lineCount%100000) == 0:
				now = time.time()
				spent = round(now - lastTime, 3 )
				logging.info( 'process:'+str(tid)+' parsed '+str(lineCount)+\
						' lines in '+str(spent)+' seconds in '+path )
		fin.close()
	
		return lineCount
	
	def __str__( self ):
		return str( self.__dict__ )

try:
	class AnlyProcess( multiprocessing.Process ):
		def __init__( self, tid, task, args, outQueue ):
			super(AnlyProcess, self).__init__()
			self.tid = tid
			self.args = args
			self.worker = AnlyWorker( tid, task, args )
			self.outQueue = outQueue
	
		def run( self ):
			(totalLineCount, ofileList) = self.worker.run()
			self.outQueue.put( (self.tid, totalLineCount, ofileList) )
	
except:
	pass
	
	
	
	
