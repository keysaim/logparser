#*********************************************************************************************#
#*********************************************************************************************#
#******************witten by Neil Hao(nbaoping@cisco.com), 2013/05/19*************************#
#*********************************************************************************************#
#*********************************************************************************************#
#*********************************************************************************************#
import logging

from analyser import *
from filter import *
from anlyhelper import *
from regexformat import *

from operator import itemgetter
#======================================================================
#===========parse xml config and create the analysers==================
#======================================================================

class OutputCfg( BaseObject ):
	def __init__( self ):
		self.idName = ''
		self.fmtName = None
		self.expType = 'raw'
		self.expTypeArgs = None
		self.mapKeys = None
		self.haveMapKeys = None
		self.sort = False
		self.split = True
		self.unitRate = 1
		self.insertValue = None
		self.outList = None
		self.calcTiming = False


class AnalyserFactory:
	anlyMap = dict()

	def __init__( self, xmlTimeStr=None ):
		self.__standardMap = {
				'bandwidth' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_bandwidth),
				'status' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_status),
				'xactrate' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_xactrate),
				'requestdes' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_requestdes),
				'consumed' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_common),
				'tmpconn' : (AnalyserFactory.__parse_tmpconn, AnalyserFactory.__create_common),
				'assemble' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_common),
				'counter' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_common),
				'activeSessions' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_active_sessions),
				'output' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_common),
				'filter' : (AnalyserFactory.__parse_dummy, AnalyserFactory.__create_common)
				}
		self.xmlTimeStr = xmlTimeStr

	def __get_parse_func( self, anlyType ):
		if anlyType in self.__standardMap:
			return ( self, self.__standardMap[ anlyType ][0] )
		if anlyType in self.anlyMap:
			return ( self.anlyMap[anlyType][2], self.anlyMap[anlyType][0] )
		return None

	def __get_create_func( self, anlyType ):
		if anlyType in self.__standardMap:
			return ( self, self.__standardMap[ anlyType ][1] )
		if anlyType in self.anlyMap:
			return ( self.anlyMap[anlyType][2], self.anlyMap[anlyType][1] )
		return None

	def create_from_args( self, args, startTime, endTime ):
		outdir = os.path.join( args.path, RES_DIR )
		if args.configPath is not None:
			args.outdir = outdir
			analysers = self.__create_from_config( args )
			logging.debug( 'total parsed analysers:'+str(len(analysers)) )
			return analysers
		analysers = list()
		num = 0
		if args.analyseType == 0:		#bandwidth 
			path = os.path.join( outdir, 'bandwidth_' + str(args.pace) + '_' + str(num) )
			anly = BandwidthAnalyser( path, startTime, endTime, args.pace )
			analysers.append( anly )
		return analysers;

	def __create_from_config( self, args ):
		analysers = list()
		configList = self.__parse_xml( args.outdir, args.configPath, args )
		for config in configList:
			config.sorted = args.sorted
			funcItem = self.__get_create_func( config.type )
			if funcItem is not None:
				anly = funcItem[1]( funcItem[0], config )
				anly.sorted = args.sorted
				anly.atype = config.type
				if config.insertValue is not None:
					anly.insertValue = config.insertValue
				analysers.append( anly )
			else:
				logging.error( 'no create function for analyser'+str(config) )
		
		logging.info( 'total parsed analysers:'+str(len(analysers)) )
		return analysers

	def __parse_gloabl_config( self, rootNode ):
		paceNode = stimeNode = etimeNode = insertNode = outNode = fmtNode = None
		for cnode in rootNode.childNodes:
			name = cnode.nodeName
			if name == 'pace':
				paceNode = cnode
			elif name == 'startTime':
				stimeNode = cnode 
			elif name == 'endTime':
				etimeNode = cnode
			elif name == 'insertValue':
				insertNode = cnode
			elif name == 'outPath':
				outNode = cnode
			elif name == 'formatter':
				fmtNode = cnode

		pace = None
		stime = None
		etime = None
		insertValue = None
		outPath = None
		formatter = None
		if paceNode:
			pace = int( get_nodevalue(paceNode) )
		if stimeNode:
			stime = seconds_str( get_nodevalue(stimeNode) )
			logging.info( 'start time:'+str_seconds( stime ) )
		if etimeNode:
			etime = seconds_str( get_nodevalue(etimeNode) )
			logging.info( 'end time:'+str_seconds( etime ) )
		if insertNode:
			insertValue = get_nodevalue(insertNode)
			logging.debug( 'global insertValue:'+insertValue )
		if outNode:
			outPath = get_nodevalue( outNode )
		if fmtNode:
			formatter = LogFormatter()
			formatter.parse_xml( fmtNode )

		return (pace, stime, etime, insertValue, outPath, formatter)

	def __parse_xml( self, inputPath, xmlfile, args ):
		configList = list()
		doc = minidom.parse( xmlfile )
		root = doc.documentElement
		anlyNodes = get_xmlnode( root, 'analyser' )
		(gpace, gstime, getime, insertValue, outPath, formatter) = self.__parse_gloabl_config( root )
		args.formatter = formatter
		logging.info( 'global config, pace:'+str(gpace)+',stime:'+\
				str(gstime)+',etime:'+str(getime)+',insertValue:'+str(insertValue)+',outPath:'+str(outPath) )
		count = 0
		total = 0
		if self.xmlTimeStr is None:
			curTimeStr = cur_timestr() + '_'
		else:
			curTimeStr = self.xmlTimeStr + '_'
		curTimeStr = curTimeStr.replace( '/', '' )
		curTimeStr = curTimeStr.replace( ':', '' )
		for node in anlyNodes:
			config = AnalyConfig()
			#load the default global config
			if gpace is not None:
				config.pace = gpace
			if gstime is not None:
				config.startTime = gstime
			if getime is not None:
				config.endTime = getime
			if insertValue is not None:
				config.insertValue = insertValue
			if outPath is not None:
				inputPath = outPath

			mkdir( inputPath )
			outsList = self.__parse_outputs_list( node )

			nodeTypeList = get_xmlnode( node, 'type' )
			if (nodeTypeList is None or len(nodeTypeList) == 0) and len(outsList) == 0:
				logging.error( 'invalid node'+str(node) )
				continue
			count += 1
			nodePaceList = get_xmlnode( node, 'pace' )
			nodeStimeList = get_xmlnode( node, 'startTime' )
			nodeEtimeList = get_xmlnode( node, 'endTime' )
			nodeInsertList = get_xmlnode( node, 'insertValue' )
			nodePath = get_xmlnode( node, 'outPath' )

			if len(nodeTypeList) > 0:
				config.type = get_nodevalue( nodeTypeList[0] )
			if nodePaceList:
				config.pace = int( get_nodevalue( nodePaceList[0] ) )
			if nodeStimeList:
				config.startTime = seconds_str( get_nodevalue( nodeStimeList[0] ) )
				logging.debug( 'start time:' + str(config.startTime) )
			if nodeEtimeList:
				config.endTime = seconds_str( get_nodevalue(nodeEtimeList[0]) )
				logging.debug( 'end time:' + str(config.endTime) )
			if nodeInsertList:
				config.insertValue = get_nodevalue(nodeInsertList[0])
			if nodePath:
				config.outPath = get_nodevalue( nodePath[0] )
			else:
				if len(nodeTypeList) == 1:
					fname = curTimeStr + '_' + str(count) + '_' + config.type + '_' + str(config.pace) + '.txt'
					config.outPath = os.path.join( inputPath, fname )

			filtersList = get_xmlnode( node, 'filters' )
			config.filter = None
			if filtersList is not None and len(filtersList) > 0:
				filtersNode= filtersList[0]
				baseFilter = BaseFilter()
				if baseFilter.parse_xml( filtersNode ):
					config.filter = baseFilter
			
			incount = 0

			#add config for output list
			for (ilist, idName) in outsList:
				nconfig = AnalyConfig()
				config.copy_object( nconfig )
				nconfig.outList = ilist
				incount += 1
				ntype = 'output'
				hashVal = self.__hash_to_int( idName )
				logging.debug( 'idName:'+idName+',hashVal:'+str(hashVal) )
				nconfig.type = ntype
				funcItem = self.__get_parse_func( ntype )
				if funcItem is not None:
					funcItem[1]( funcItem[0], nconfig, node )
				fname = curTimeStr + '_' + str(count) + '_' + str(incount) + '_' + \
						ntype + str(hashVal) + '_' + str(nconfig.pace) + '_out_.txt'
				nconfig.outPath = os.path.join( inputPath, fname )
				logging.info( 'parsed anlyser'+str(nconfig) )
				configList.append( nconfig )

			ownFile = len(nodeTypeList) > 1
			#add config for type list
			for typeNode in nodeTypeList:
				nconfig = AnalyConfig()
				config.copy_object( nconfig )
				incount += 1
				ntype = get_nodevalue( typeNode )
				nconfig.type = ntype
				funcItem = self.__get_parse_func( ntype )
				if funcItem is not None:
					funcItem[1]( funcItem[0], nconfig, node )
				if ownFile:
					fname = curTimeStr + '_' + str(count) + '_' + str(incount) + '_' + ntype + '_' + str(nconfig.pace) + '.txt'
					nconfig.outPath = os.path.join( inputPath, fname )
				logging.info( 'parsed anlyser'+str(nconfig) )
				configList.append( nconfig )

			total += incount
		logging.info( 'total '+str(total)+' Analysers parsed' )
		return configList

	def __hash_to_int( self, ostr ):
		idx = 0
		hashVal = 0
		while idx < len(ostr):
			cval = ord( ostr[idx] )
			hashVal += cval*(idx+1)
			idx += 1

		return hashVal

	def __parse_outputs_list( self, node ):
		outsList = list()
		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'outputs':
				outListInfo = self.__parse_outputs( cnode )
				outsList.append( outListInfo )
		
		return outsList

	def __parse_outputs( self, node ):
		outList = list()
		idName = ''
		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'output':
				ocfg = self.__parse_output( cnode )
				idName += '_' + ocfg.idName
				outList.append( ocfg )

		outList = self.__check_raw_in_list( outList )

		return (outList, idName)


	def __parse_output( self, node ):
		ocfg = OutputCfg()
		outList = list()

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name.startswith( '#' ):
				continue

			value = get_nodevalue( cnode )
			if name == 'fmtName':
				ocfg.fmtName = std_fmt_name( value )
				ocfg.idName += ocfg.fmtName
			elif name == 'expType':
				ocfg.expType = value
				ocfg.idName += '_' + value
			elif name == 'expTypeArgs':
				ocfg.expTypeArgs = value
			elif name == 'mapKeys':
				ocfg.mapKeys = value
				ocfg.haveMapKeys = True
			elif name == 'notMapKeys':
				ocfg.mapKeys = value
				ocfg.haveMapKeys = False
			elif name == 'sort':
				val = int( value )
				ocfg.sort = val > 0
			elif name == 'split':
				ocfg.split = int( value )
			elif name == 'insertValue':
				ocfg.insertValue = value
			elif name == 'unitRate':
				ocfg.unitRate = float( value )
			elif name == 'timing':
				val = int( value )
				ocfg.calcTiming = (val > 0)
			elif name == 'output':
				cocfg = self.__parse_output( cnode )
				ocfg.idName += '_' + cocfg.idName
				outList.append( cocfg )

		if len(outList) > 0:
			logging.debug( '**************&&&&&&&&&&&&&'+str(outList) )
			outList = self.__check_raw_in_list( outList )
			ocfg.outList = outList
			logging.debug( '**************&&&&&&&&&&&&&'+str(outList) )
		
		return ocfg

	#in raw mode, only raw expType is allowed
	def __check_raw_in_list( self, outList ):
		rawList = list()
		ridList = list()
		for ocfg in outList:
			if ocfg.expType == 'raw':
				rawList.append( ocfg )
			else:
				ridList.append( ocfg )

		if len(rawList) > 0:
			for ocfg in ridList:
				logging.warn( '***********only raw ouput is allowed, will engore the output type'+str(ocfg.expType) )
			return rawList

		return outList

	def __parse_outputs_old( self, node ):
		nlist = get_xmlnode( node, 'outputs' )
		outList = list()
		for onode in nlist:
			inodeList = get_xmlnode( onode, 'output' )
			ilist = list()
			hasRaw = False
			for inode in inodeList:
				ocfg = OutputCfg()
				fnodeList = get_xmlnode( inode, 'fmtName' )
				if len(fnodeList) > 0:
					fnode = fnodeList[0]
					ocfg.fmtName = get_nodevalue( fnode )
					ocfg.fmtName = std_fmt_name( ocfg.fmtName )
				tlist = get_xmlnode( inode, 'expType' )
				if len(tlist) > 0:
					ocfg.expType = get_nodevalue( tlist[0] )
				else:
					ocfg.expType  = 'raw'

				slist = get_xmlnode( inode, 'split' )
				if len(slist) > 0:
					ocfg.split = int( get_nodevalue(slist[0]) )
				else:
					ocfg.split = True
				insertList = get_xmlnode( inode, 'insertValue' )
				if len(insertList) > 0:
					ocfg.insertValue = get_nodevalue(insertList[0])
				else:
					ocfg.insertValue = None

				rateList = get_xmlnode( inode, 'unitRate' )
				if len(rateList) > 0:
					ocfg.unitRate = float( get_nodevalue(rateList[0]) )
				else:
					ocfg.unitRate = 1

				logging.debug( ocfg )
				if ocfg.expType == 'raw':
					hasRaw = True
				elif hasRaw:
					logging.warn( '***********only raw ouput is allowed, will engore the output type'+str(ocfg.expType) )
					continue
				ilist.append( ocfg )
			
			if len(ilist) > 0:
				outList.append( ilist )

		return outList

	def __create_bandwidth( self, config ):
		anly = BandwidthAnalyser( config )
		return anly

	def __create_active_sessions( self, config ):
		anly = ActiveSessionsAnalyser( config )
		return anly
	
	def __create_status( self, config ):
		anly = StatusAnalyser( config )
		return anly

	def __create_xactrate( self, config ):
		anly = XactRateAnalyser( config )
		return anly

	def __create_requestdes( self, config ):
		helper = DesHelper()
		anly = SingleAnalyser( config, helper )
		return anly

	def __parse_dummy( self, config, node ):
		pass

	def __parse_tmpconn( self, config, node ):
		snode = get_xmlnode( node, 'servTime' )
		servTime = int( get_nodevalue(snode[0]) )
		config.servTime = servTime

		cnodeList = get_xmlnode( node, 'client' )
		cmap = None
		if cnodeList is not None:
			for cnode in cnodeList:
				cip = get_nodevalue( cnode )
				if cip == 'all':
					cmap = dict()
					cmap['all'] = 0
					break
				else:
					if cmap is None:
						cmap = dict()
					cmap[cip] = 0
		if cmap is not None:
			config.clientMap = cmap

		tnode = get_xmlnode( node, 'thresCount' )
		if len(tnode) > 0:
			config.thresCount = get_nodevalue( tnode[0] )


	def __create_common( self, config ):
		atype = 'single'
		helper = None
		anly = None
		if config.type == 'consumed':
			helper = ConsumedHelper()
		elif config.type == 'tmpconn':
			helper = TmpconnHelper( config )
		elif config.type == 'assemble':
			helper = AssembleHelper( )
		elif config.type == 'counter':
			helper = CounterHelper()
		elif config.type == 'output':
			ocfg = config.outList[0]
			if ocfg.expType == 'raw':
				#for raw type, all the others are raw types
				helper = RawOutputHelper( config.outList )
			else:
				helper = OutputsHelper( config.outList, config.pace )
		elif config.type == 'filter':
			anly = FilterAnalyser( config )
			return anly

		helper.sorted = config.sorted

		if atype == 'single':
			anly = SingleAnalyser( config, helper )
		return anly

def register_anlyser( anlyType, parse_func, create_func, obj ):
	AnalyserFactory.anlyMap[anlyType] = ( parse_func, create_func, obj )





