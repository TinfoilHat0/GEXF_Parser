import queue
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
		self.nStaticNodes = 0

	def read(self, fpath):
		"""Reads and returns the graph object defined in fpath"""
		doc = minidom.parse(fpath)
		#1. Determine if graph is dynamic&directed
		graph = doc.getElementsByTagName("graph")[0]
		if (graph.getAttribute("defaultedgetype") == "directed"):
			self.directed = True
		if (graph.getAttribute("mode") == "dynamic"):
			self.dynamic = True

		#2.Read edges and determine if graph is weighted
		edges = doc.getElementsByTagName("edge")
		for e in edges:
			u = e.getAttribute("source")
			v = e.getAttribute("target")
			w = "1.0"
			if e.hasAttribute("weight"):
				self.weighted = True
				w = e.getAttribute("weight")
			if self.dynamic:
				#fix here
				self.handleDynamics(e, "e", u, v, w)
			else:
				self.q.put(u, v, w))

		#3. Create graph object
		self.g = nt.Graph(0, self.weighted, self.directed)

		#4. Read nodes
		nodes = doc.getElementsByTagName("node")
		for n in nodes:
			if self.dynamic:
				#fix here
				self.handleDynamics(n, "n", self.nStaticNodes, 0, 0)
			else:
				val = n.getAttribute("id")
				self.mapping[val] = self.nStaticNodes
			self.nStaticNodes +=1
		#print(self.eventStream)

		#5. Add initial edges&nodes
		for i in range(0, self.nStaticNodes):
			self.g.addNode()
		while not self.q.empty():
			edge = self.q.get()
			(u, v, w) = (edge[0], edge[1], float(edge[2]))
			self.g.addEdge(self.mapping[u], self.mapping[v], w)
			self.nStaticNodes = 0
		return self.g


	def createEvent(self, eventTime, eventType, u, v, w):
		(event, u, v, w) = (" ", int(u), int(v), float(w))
		if eventType == "an":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.NODE_ADDITION, 0, 0, 0)
		elif eventType == "dn":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.NODE_REMOVAL, u, 0, 0)
		elif eventType == "ae":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.EDGE_ADDITION, u, v, w)
		elif eventType == "de":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.EDGE_REMOVAL, u, v, w)
		elif eventType == "ce":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.EDGE_WEIGHT_UPDATE, u, v, w)
		elif eventType == "st":
			event = nt.dynamic.GraphEvent(nt.dynamic.GraphEvent.TIME_STEP, u, v, w)
		self.eventStream.append((event, eventTime))

	def handleDynamics(self, element, elementType, u, v, w):
		""" element:Parsed element from XML file,
			elementType: n(node) or e(edge),
			u,v,w: nodes and weight
		Determine the operations as follows:
			1.Element has start:Create add event
			2.Element has end:Create del event
			3.If element has only end or no start&end, add it to the initial graph
		"""
		if element.hasAttribute("start"):
			self.createEvent(element.getAttribute("start"), "a"+elementType, u, v, w)
			if element.hasAttribute("end"):
				self.createEvent(element.getAttribute("end"), "d"+elementType, u, v, w)
		else:
			if (elementType == "n"):
				self.nStaticNodes += 1
			elif (elementType == "e"):
				self.q.put((u,v,w))
			if element.hasAttribute("end"):
				self.createEvent(element.getAttribute("end"), "d"+elementType, u, v, w)
		if element.hasChildNodes():
			spells = element.getElementsByTagName("spell")
			for s in spells:
				if s.hasAttribute("start"):
					self.createEvent(s.getAttribute("start"), "a"+elementType, u, v, w)
					if s.hasAttribute("end"):
						self.createEvent(s.getAttribute("end"), "d"+elementType, u, v, w)
				else:
					if (elementType == "n"):
						self.nStaticNodes += 1
					elif (elementType == "e"):
						if self.weighted:
							self.q.put((u,v,w))
					if s.hasAttribute("end"):
						self.createEvent(s.getAttribute("end"), "d"+elementType, u, v, w)
		if(elementType == "n"):
			val = element.getAttribute("id")
			self.mapping[val] = u

# GEXFWriter
class GEXFWriter:
	""" This class provides a function to write a NetworKit graph to a file in the
		GEXF format. """

	def __init__(self):
		""" Initializes the class. """
		self.edgeIdctr = 0
		self.dir_str = ''

	def write(self, graph, fname):
		""" Writes a NetworKit graph to the specified file fname.
			Parameters:
				- graph: a NetworKit::Graph python object
				- fname: the desired file path and name to be written to
		"""
		# reset some internal variables in case more graphs are written with the same instance
		self.edgeIdctr = 0
		self.dir_str = ''

		# start with the root element and the right header information
		root = ET.Element('gexf')
		root.set("xmlns:xsi","http://www.w3.org/2001/XMLSchema-instance")
		root.set("xsi:schemaLocation","http://www.gexf.net/1.1draft " \
			"http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd")

		# create graph element with appropriate information
		graphElement = ET.SubElement(root,"graph")
		if graph.isDirected():
			graphElement.set('defaultedgetype', 'directed')
			self.dir_str = 'true'
		else:
			graphElement.set('defaultedgetype', 'undirected')
			self.dir_str = 'false'

		# Add nodes
		nodesElement = ET.SubElement(graphElement, "nodes")
		for n in graph.nodes():
			nodeElement = ET.SubElement(nodesElement,'node')
			nodeElement.set('id', str(n))

		# Add edges
		edgesElement = ET.SubElement(graphElement, "edges")
		if graph.isWeighted():
			for e in graph.edges():
				edgeElement = ET.SubElement(edgesElement,'edge')
				edgeElement.set('target', str(e[1]))
				edgeElement.set('source', str(e[0]))
				edgeElement.set('id', "{0}".format(self.edgeIdctr))
				self.edgeIdctr += 1
				edgeElement.set('weight', str(graph.weight(e[0],e[1])))
		else:
			for e in graph.edges():
				edgeElement = ET.SubElement(edgesElement,'edge')
				edgeElement.set('target', str(e[1]))
				edgeElement.set('source', str(e[0]))
				edgeElement.set('id', "{0}".format(self.edgeIdctr))
				self.edgeIdctr += 1

	#TODO: optional prettify function for formatted output of xml files
		tree = ET.ElementTree(root)
		tree.write(fname,"utf-8",True)
