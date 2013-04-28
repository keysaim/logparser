from datetime import timedelta
import os
from cStringIO import StringIO
from  xml.dom import  minidom

from base import *
from sampler import *

BUF_TIME = 36000		#in seconds
NUM_THRES = 36000


class AnalyConfig( object ):
	def __init__( self ):
		self.type = ''
		self.startTime = 0
		self.endTime = -1
		self.pace = 0
		self.outPath = ''

	def __str__( self ):
		return str( self.__dict__ )

class Analyser( object ):
	def __init__( self, config, toFile = True ):
		self.startTime = config.startTime
		self.endTime = config.endTime
		self.pace = config.pace
		if toFile:
			self.outPath = config.outPath
			self.fout = open( config.outPath, 'w' )
			print self.fout

	def __str__( self ):
		buf = 'startTime:' + str(self.startTime) + ','
		buf += 'endTime:' + str(self.endTime) + ','
		buf += 'pace:' + str(self.pace)
		if 'outPath' in self.__dict__:
			buf += ',outPath:' + self.outPath
		return buf

	def get_sample_start_time( self, logInfo ):
		startTime = self.startTime
		if startTime <= 0:
			startTime = logInfo.rtime - BUF_TIME
		return startTime

	def get_sample_end_time( self, logInfo ):
		return self.endTime

	def analyse_log( self, logInfo ):
		#control the startTime
		if self.startTime > 0:
			etime = logInfo.rtime + logInfo.stime / 1000000
			if etime < self.startTime:
				return False
		#control the endTime
		if self.endTime > 0:
			if logInfo.rtime > self.endTime:
				return False
		if self.pace == 0:
			return self.anly_zero_pace( logInfo )
		elif self.pace < 0:
			return self.anly_negative_pace( logInfo )
		else:
			return self.anly_pace( logInfo )

	def anly_zero_pace( self, logInfo ):
		raise Exception( 'derived must implement anly_zero_pace virtual function' )

	def anly_negative_pace( self, logInfo ):
		raise Exception( 'derived must implement anly_negative_pace virtual function' )

	def anly_pace( self, logInfo ):
		raise Exception( 'derived must implement anly_pace virtual function' )

	def close( self ):
		raise Exception( 'derived must implement close virtual function' )


class BandwidthAnalyser( Analyser ):
	def __init__( self, config ):
		super( BandwidthAnalyser, self ).__init__( config )
		self.totalSent = 0
		self.sampler = None
		self.hasWritten = False

	def anly_zero_pace( self, logInfo ):
		servTime = logInfo.stime / 1000000.0		#to second
		sampleTime = logInfo.rtime
		totalSent = logInfo.allSent
		#print 'total sent:', self.totalSent, 'serv time:', self.servTime
		band = totalSent * 8.0 / servTime / 1024 / 1024
		band = round( band, 3 )
		dtime = to_datetime( sampleTime )
		log = str_time( dtime ) + '\t' + str( band ) + '\t' + str(servTime) + '\t' + str(totalSent) + '\n'
		self.fout.write( log )
		return True

	def anly_negative_pace( self, logInfo ):
		if self.sampler is None:
			self.__create_sampler( logInfo )
		servTime = logInfo.stime / 1000000
		if servTime == 0:
			servTime = 1
		value = logInfo.allSent
		#print 'servTime', servTime, 'num', num, logInfo.stime, value
		if self.sampler.add_sample( logInfo.rtime, value ) != 0:
			return False
		return True

	def anly_pace( self, logInfo ):
		if self.sampler is None:
			self.__create_sampler( logInfo )
		servTime = logInfo.stime / 1000000
		if servTime == 0:
			servTime = 1
		num = servTime / self.sampler.pace + 1
		value = logInfo.allSent / float(num)
		#print 'servTime', servTime, 'num', num, logInfo.stime, value
		ret = self.sampler.add_samples( logInfo.rtime, value, num )
		if ret < 0:
			if self.hasWritten:
				print 'old log', logInfo
			return False	#TODO
		elif ret > 0:		#need to flash the buffer to the file
			ctime = logInfo.rtime
			while ret > 0:
				ctime += ret * self.sampler.pace
				num -= ret
				ret = self.sampler.add_samples( ctime, value, num )
		return True

	def __create_sampler( self, logInfo ):
		startTime = self.get_sample_start_time( logInfo )
		endTime = self.get_sample_end_time( logInfo )
		sargs = SamplerArgs( startTime, endTime, self.pace,
				BUF_TIME, NUM_THRES, BandwidthAnalyser.__flush_callback, self )
		self.sampler = Sampler( sargs )

	def __flush_callback( self, sampler, blist ):
		curTime = sampler.startTime
		toAdd = 0
		if sampler.pace > 0:
			toAdd = sampler.pace / 2
		bufio = StringIO()
		print 'flush buffer, curTime:', str_seconds(curTime), 'size:', len(blist)
		for value in blist:
			#print 'flash value', value
			if value != 0:
				#print 'dump log', curTime, value
				dtime = to_datetime( curTime + toAdd )
				tstr = str_time( dtime )
				band = round( value * 8 / float(sampler.pace) / 1024 / 1024, 3 )
				bufio.write( tstr )
				bufio.write( '\t' )
				bufio.write( str(band) )
				bufio.write( '\t' )
				bufio.write( str(curTime) )
				bufio.write( '\n' )
			curTime += sampler.pace
		ostr = bufio.getvalue()
		self.fout.write( ostr )
		self.hasWritten = True

	def close( self ):
		print 'close', self.__class__, self
		if self.sampler is not None:
			#print self.sampler.slist1
			#print self.sampler.slist2
			self.sampler.flush()
			self.sampler = None
		self.fout.close()



class StatusAnalyser( Analyser ):
	def __init__( self, config ):
		super( StatusAnalyser, self ).__init__( config )
		self.sampler = None

	def anly_zero_pace( self, logInfo ):
		tstr = str_seconds( logInfo.rtime )
		log = tstr + ',' + str(logInfo) + '\n'
		self.fout.write( log )
		return True

	def anly_negative_pace( self, logInfo ):
		return self.anly_pace( logInfo )

	def anly_pace( self, logInfo ):
		if self.sampler is None:
			self.__create_sampler( logInfo )
		value = dict()
		value[logInfo.status] = 1
		servTime = logInfo.stime / 1000000 + 1
		ret = self.sampler.add_sample( logInfo.rtime + servTime, value )
		if ret != 0:
			return False
		return True

	def __create_sampler( self, logInfo ):
		startTime = self.get_sample_start_time( logInfo )
		endTime = self.get_sample_end_time( logInfo )
		sargs = SamplerArgs( startTime, endTime, self.pace,
				BUF_TIME, NUM_THRES, StatusAnalyser.__flush_callback, self )
		self.sampler = MutableSampler( sargs, StatusAnalyser.__init_value, StatusAnalyser.__update_value )

	def __init_value( self, value ):
		return dict()
	
	def __update_value( self, oldValue, sampleValue ):
		for status in sampleValue.keys():
			count = sampleValue[ status ]
			if status in oldValue:
				count += oldValue[ status ]
			oldValue[status] = count
		return oldValue

	def __flush_callback( self, sampler, blist ):
		curTime = sampler.startTime
		toAdd = 0
		if sampler.pace > 0:
			toAdd = sampler.pace / 2
		bufio = StringIO()
		print 'flush buffer, curTime:', str_seconds(curTime), 'size:', len(blist)
		for item in blist:
			if len(item) != 0:
				sampleTime = curTime + toAdd
				tstr = str_seconds( sampleTime )
				bufio.write( tstr )
				bufio.write( ',' )
				bufio.write( str(item) )
				bufio.write( '\n' )
			curTime += sampler.pace
		logs = bufio.getvalue()
		self.fout.write( logs )

	def close( self ):
		print 'close', self.__class__, self
		if self.sampler is not None:
			self.sampler.flush()
			self.sampler = None
		self.fout.close()


class XactRateAnalyser( Analyser ):
	def __init__( self, config ):
		super( XactRateAnalyser, self ).__init__( config )
		self.sampler = None

	def anly_zero_pace( self, logInfo ):
		tstr = str_seconds( logInfo.rtime )
		log = tstr + ',' + str(logInfo) + '\n'
		self.fout.write( log )
		return True

	def anly_negative_pace( self, logInfo ):
		return self.anly_pace( logInfo )

	def anly_pace( self, logInfo ):
		if self.sampler is None:
			self.__create_sampler( logInfo )
		ret = self.sampler.add_sample( logInfo.rtime, 1 )
		if ret != 0:
			return False
		return True

	def __create_sampler( self, logInfo ):
		startTime = self.get_sample_start_time( logInfo)
		endTime = self.get_sample_end_time( logInfo )
		sargs = SamplerArgs( startTime, endTime, self.pace,
				BUF_TIME, NUM_THRES, XactRateAnalyser.__flush_callback, self )
		self.sampler = Sampler( sargs )

	def __flush_callback( self, sampler, blist ):
		curTime = sampler.startTime
		toAdd = 0
		if sampler.pace > 0:
			toAdd = sampler.pace / 2
		bufio = StringIO()
		print 'flush buffer, curTime:', str_seconds(curTime), 'size:', len(blist)
		for item in blist:
			if item > 0:
				sampleTime = curTime + toAdd
				tstr = str_seconds( sampleTime )
				bufio.write( tstr )
				bufio.write( ',' )
				bufio.write( str(item) )
				bufio.write( '\n' )
			curTime += sampler.pace
		logs = bufio.getvalue()
		self.fout.write( logs )

	def close( self ):
		print 'close', self.__class__, self
		if self.sampler is not None:
			self.sampler.flush()
			self.sampler = None
		self.fout.close()


