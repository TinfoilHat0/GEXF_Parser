import unittest
import os


class TestGEXFIO(unittest.TestCase):
	def setUp(self):
		from GEXFIO import GEXFReader
		self.reader = GEXFReader()
		#celegans.gexf from http://gexf.net/format/datasets.html
		self.g, self.events = self.reader.read("input/staticTest.gexf")
		#dynamics.gexf from http://gexf.net/format/datasets.html
		self.g2, self.events2 = self.reader.read("input/dynamicTest.gexf")
		#a random dynamic gexf file generated by gephi with dynamic weights
		self.g3, self.events3 = self.reader.read("input/dynamicTest2.gexf")
		#a simple dynamic weighted graph
		self.g4, self.events4 = self.reader.read("input/dynamicTest3.gexf")


	def checkStatic(self, graph, graph2):
		self.assertEqual(graph.isDirected(), graph2.isDirected())
		self.assertEqual(graph.isWeighted(), graph2.isWeighted())
		self.assertEqual(graph.numberOfNodes(), graph2.numberOfNodes())
		self.assertEqual(graph.edges(), graph2.edges())

	def checkDynamic(self, eventStream, eventStream2):
		from _NetworKit import GraphEvent
		self.assertEqual(len(eventStream), len(eventStream2))
		#Check if timesteps are occuring at the same indexes
		index = 0
		for i in range(0, len(eventStream)):
			event = eventStream[i]
			event2 = eventStream2[i]
			if event.type == GraphEvent.TIME_STEP:
				self.assertEqual(GraphEvent.TIME_STEP, event2.type)
				old_index = index
				index = i
				#check if # of events between each timestep is equal
				self.assertEqual(len(eventStream[old_index:index]),
					len(eventStream2[old_index:index]))


	def test(self):
		from GEXFIO import GEXFWriter
		#write and read files again to check
		writer = GEXFWriter()
		writer.write(self.g, "output/staticTestResult.gexf", self.events)
		self.assertTrue(os.path.isfile("output/staticTestResult.gexf"))
		writer.write(self.g2, "output/dynamicTestResult.gexf", self.events2)
		self.assertTrue(os.path.isfile("output/dynamicTestResult.gexf"))
		writer.write(self.g3, "output/dynamicTest2Result.gexf", self.events3)
		self.assertTrue(os.path.isfile("output/dynamicTest2Result.gexf"))
		writer.write(self.g4, "output/dynamicTest3Result.gexf", self.events4)
		self.assertTrue(os.path.isfile("output/dynamicTest3Result.gexf"))


		gTest, testEvents = self.reader.read("output/staticTestResult.gexf")
		g2Test, testEvents2 = self.reader.read("output/dynamicTestResult.gexf")
		g3Test, testEvents3 = self.reader.read("output/dynamicTest2Result.gexf")
		g4Test, testEvents4 = self.reader.read("output/dynamicTest3Result.gexf")

		#1. check properties and static elements
		self.checkStatic(self.g, gTest)
		self.checkStatic(self.g2, g2Test)
		self.checkStatic(self.g3, g3Test)
		self.checkStatic(self.g4, g4Test)
		#2.check events
		self.checkDynamic(self.events, testEvents)
		self.checkDynamic(self.events2, testEvents2)
		self.checkDynamic(self.events3, testEvents3)
		self.checkDynamic(self.events4, testEvents4)






if __name__ == "__main__":
	unittest.main()
