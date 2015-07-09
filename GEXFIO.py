import queue
import datetime
import xml.etree.cElementTree as ET
from xml.dom import minidom
import networkit as nt


# GEXF Reader
class GEXFReader:
	def __init__(self):
		""" Initializes the GEXFReader class """
		self.mapping = dict()
		self.g = nt.Graph(0)
		self.weighted = False
		self.directed = False
		self.dynamic = False
		self.q = queue.Queue()
		self.eventStream = []
		self.nInitialNodes = 0

	def read(self, fpath):
		"""Reads and returns the graph object defined in fpath"""
		#0. Reset internal vars and parse the xml
		self.mapping.clear()
		self.g = nt.Graph(0)
		self.weighted, self.directed, self.dynamic = False, False, False
		self.eventStream.clear()
		self.nInitialNodes = 0
		doc = minidom.parse(fpath)

		#1. Determine if graph is dynamic and directed
		graph = doc.getElementsByTagName("graph")[0]
		if (graph.getAttribute("defaultedgetype") == "directed"):
			self.directed = True
		if (graph.getAttribute("mode") == "dynamic"):
			self.dynamic = True

		#2. Read nodes and map them to their id's defined in the file
		nodes = doc.getElementsByTagName("node")
		for n in nodes:
			_id = n.getAttribute("id")
			if self.dynamic:
				self.mapping[_id] = int(_id)
				self.handleDynamics(n, "n", _id, "0", "0")
			else:
				self.mapping[_id] = self.nInitialNodes
				self.nInitialNodes +=1
		if self.dynamic:
			self.mapDynamicNodes()


		#3.Read edges and determine if graph is weighted
		edges = doc.getElementsByTagName("edge")
		for e in edges:
			u = e.getAttribute("source")
			v = e.getAttribute("target")
			w = "1.0"
			if e.hasAttribute("weight"):
				self.weighted = True
				w = e.getAttribute("weight")
			if self.dynamic:
				self.handleDynamics(e, "e", u, v, w)
			else:
				self.q.put((u, v, w))

		#4. Create graph object
		self.g = nt.Graph(0, self.weighted, self.directed)

		#5. Add initial edges and nodes to the graph and sort the eventStream by time
		#5.1 Adding initial edges and nodes
		for i in range(0, self.nInitialNodes):
			self.g.addNode()
		while not self.q.empty():
			edge = self.q.get()
			(u, v, w) = (edge[0], edge[1], float(edge[2]))
			self.g.addEdge(self.mapping[u], self.mapping[v], w)

		#5.2 Sorting th eventStream by time and adding timesteps between events that happen in different times
		self.eventStream.sort(key=lambda x:x[1])
		for i in range(1, len(self.eventStream)):
			if self.eventStream[i][1] != self.eventStream[i-1][1]:
				self.eventStream.append((nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.TIME_STEP, 0, 0, 0), self.eventStream[i-1][1] ))
		self.eventStream.sort(key=lambda x:x[1])
		self.eventStream = [event[0] for event in self.eventStream]

		return (self.g, self.eventStream)


	def createEvent(self, eventTime, eventType, u, v, w):
		(event, u, v, w) = (" ", self.mapping[u], self.mapping[v], float(w))
		if eventType == "an":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.NODE_ADDITION, u, v, w)
		elif eventType == "dn":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.NODE_REMOVAL, u, v, w)
		elif eventType == "rn":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.NODE_RESTORATION, u, v, w)
		elif eventType == "ae":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.EDGE_ADDITION, u, v, w)
		elif eventType == "de":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.EDGE_REMOVAL, u, v, w)
		self.eventStream.append((event, eventTime))


	def handleDynamics(self, element, elementType, u, v, w):
		"""
			Determine the operations as follows:
			1.Element has start:Create add event
			2.Element has end:Create del event
			3.If element has only end or no start&end, add it to the initial graph
			4.If an element is added after it's deleted, use restoreNode
		"""

		mapped, deleted, added = False, False, False
		#parser for dynamic elements that are defined with spell attributes
		if element.hasChildNodes():
			spells = element.getElementsByTagName("spell")
			for s in spells:
				if s.hasAttribute("start"):
					if not deleted:
						self.createEvent(s.getAttribute("start"), "a"+elementType, u, v, w)
					else:
						#readding a deleted node requires restoration(to keep ids consistent during the lifetime of the graph)
						self.createEvent(s.getAttribute("start"), "r"+elementType, u, v, w)
					if s.hasAttribute("end"):
						self.createEvent(s.getAttribute("end"), "d"+elementType, u, v, w)
						deleted = True
				else:
					if (elementType == "n" and not mapped):
						self.mapping[u] = self.nInitialNodes
						self.nInitialNodes += 1
						mapped = True
					elif (elementType == "e" and not added):
						self.q.put((u,v,w))
						added = True
					if s.hasAttribute("end"):
						self.createEvent(s.getAttribute("end"), "d"+elementType, u, v, w)
						deleted = True
		#parser for dynamic elements that are defined with inline attributes
		else:
			if element.hasAttribute("start"):
				if not deleted:
					self.createEvent(element.getAttribute("start"), "a"+elementType, u, v, w)
				else:
					#readding a deleted node requires restoration(to keep ids consistent during the lifetime of the graph)
					self.createEvent(element.getAttribute("start"), "r"+elementType, u, v, w)
				if element.hasAttribute("end"):
					self.createEvent(element.getAttribute("end"), "d"+elementType, u, v, w)
					deleted = True
			else:
				if (elementType == "n" and not mapped):
					self.mapping[u] = self.nInitialNodes
					self.nInitialNodes += 1
					print(self.nInitialNodes)
					mapped = True
				elif (elementType == "e" and not added):
					self.q.put((u,v,w))
					added = True
				if element.hasAttribute("end"):
					self.createEvent(element.getAttribute("end"), "d"+elementType, u, v, w)
					deleted = True

	def mapDynamicNodes(self):
		"""
		Node id of a dynamic node must be determined before it's mapped to its gexf id.
		This requires processing the sorted eventStream and figuring out the addition order
		of the nodes.

		"""
		self.eventStream.sort(key=lambda x:x[1])
		nNodes = self.nInitialNodes
		for i in range(len(self.eventStream)):
			event = self.eventStream[i]
			if event[0].type == 0:
				_id = str(event[0].u)
				self.mapping[_id] = nNodes
				#reconstruct the event once the correct node id is determined
				mappedEvent = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.NODE_ADDITION, nNodes, 0, 0)
				self.eventStream[i] = (mappedEvent, event[1])
				nNodes += 1



# GEXFWriter
class GEXFWriter:
	""" This class provides a function to write a NetworKit graph to a file in the
		GEXF format. """

	def __init__(self):
		""" Initializes the class. """
		self.edgeIdctr = 0
		self.q = queue.Queue()

	def write(self, graph, fname, eventStream = None):
		"""
			Writes a NetworKit graph to the specified file fname.
			Parameters:
				- graph: a NetworKit::Graph python object
				- fname: the desired file path and name to be written to

		"""
		#0. reset some internal variables in case more graphs are written with the same instance
		self.edgeIdctr = 0

		#1. start with the root element and the right header information
		root = ET.Element('gexf')
		root.set("xmlns:xsi","http://www.w3.org/2001/XMLSchema-instance")
		root.set("xsi:schemaLocation","http://www.gexf.net/1.2draft http://www.gexf.net/1.2draft/gexf.xsd")

		#2. create graph element with appropriate information
		graphElement = ET.SubElement(root,"graph")
		if graph.isDirected():
			graphElement.set('defaultedgetype', 'directed')
		else:
			graphElement.set('defaultedgetype', 'undirected')
		if eventStream != None:
			graphElement.set('mode', 'dynamic')
			graphElement.set('timeformat', 'double')

		#3. Add nodes
		nodesElement = ET.SubElement(graphElement, "nodes")
		nDynamicNodes = 0 #indicates number of nodes added after graph is initialized
		if eventStream != None:
			for event in eventStream:
				if event.type == 0:
					nDynamicNodes +=1
		nNodes = len(graph.nodes()) + nDynamicNodes
		for n in range(nNodes):
			nodeElement = ET.SubElement(nodesElement,'node')
			nodeElement.set('id', str(n))
			self.writeEvent(nodeElement, eventStream, n)

		#4. Add edges
		edgesElement = ET.SubElement(graphElement, "edges")
		#4.1 Put all edges into a queue(inital + dynamic edges)
		for e in graph.edges():
			self.q.put(e)
		for event in eventStream:
			if event.type == 2:#edge addition event
				self.q.put((event.u, event.v, event.w))
		#4.2 Write edges to the gexf file
		while not self.q.empty():
			edgeElement = ET.SubElement(edgesElement,'edge')
			e = self.q.get()
			edgeElement.set('source', str(e[0]))
			edgeElement.set('target', str(e[1]))
			edgeElement.set('id', "{0}".format(self.edgeIdctr))
			self.edgeIdctr += 1
			if graph.isWeighted():
				edgeElement.set('weight', str(graph.weight(e[2])))
			self.writeEvent(edgeElement, eventStream, e)

		#5. Write the generated tree to the file
		tree = ET.ElementTree(root)
		tree.write(fname,"utf-8",True)


	def writeEvent(self, xmlElement, eventStream, graphElement):
		"""
			Determine the correct tag(start/end) as follows:
			ADDITION, RESTORATION : start
			DELETION : end

		"""
		matched = False #a var that indicates if the event belongs the graph element we traverse on
		tagged, spellsElement, timeSteps = False, None, 0
		startEvents = [0, 2, 6] #add node/edge and restore node events
		endEvents = [1, 3] #delete node/edge events

		for event in eventStream:
			if event.type == 5: #timestep event
				timeSteps += 1
			if type(graphElement) == type(0): #a node is an integer
				matched = (event.type in [0, 1, 6] and event.u == graphElement)
			else:
				matched = (event.type in [2, 3] and (event.u == graphElement[0] and event.v == graphElement[1]))
			if matched:
				if not tagged:
					spellsElement = ET.SubElement(xmlElement, "spells")
					tagged = True
				spellElement = ET.SubElement(spellsElement, "spell")
				if event.type in startEvents:
					spellElement.set("start", str(timeSteps))
				if event.type in endEvents:
					spellElement.set("end", str(timeSteps))
