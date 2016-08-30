"""
/***************************************************************************
Name			 	 : qpalsSection
Description          : GUI for opals module "section"
Date                 : 2016-08-29
copyright            : (C) 2016 by Lukas Winiwarter/TU Wien
email                : lukas.winiwarter@tuwien.ac.at
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 """

from PyQt4 import QtCore, QtGui

from qgis.core import *
from qgis.gui import *

import os, tempfile
from xml.dom import minidom
import matplotlib.pyplot as plt
import numpy as np
import ogr

import QpalsShowFile, QpalsModuleBase, QpalsDropTextbox, QpalsParameter

class QpalsSection:

    def __init__(self, project, layerlist, iface):
        self.advanced_widget = None
        self.simple_widget = None
        self.tabs = None
        self.project = project
        self.layerlist = layerlist
        self.iface = iface
        self.visLayer= None
        self.ltool = LineTool(self.iface.mapCanvas(), self.visLayer, secInst=self)
        self.sections = dict()

    def createWidget(self):
        self.advanced_widget = QtGui.QDialog()
        self.simple_widget = QtGui.QDialog()
        self.tabs = QtGui.QTabWidget()
        ### SIMPLE ###
        ls = QtGui.QFormLayout()
        ls.addRow(QtGui.QLabel("Choose input file:"))
        self.txtinfileSimple = QpalsDropTextbox.QpalsDropTextbox(layerlist=self.layerlist)
        ls.addRow(QtGui.QLabel("Input file (odm)"), self.txtinfileSimple)
        self.runShdBtnSimple = QtGui.QPushButton("Load File")
        self.runShdBtnSimple.clicked.connect(self.loadShading)
        ls.addRow(self.runShdBtnSimple)
        self.txtthickness = QtGui.QLineEdit("5")
        ls.addRow(QtGui.QLabel("Section thickness [m]"), self.txtthickness)
        self.linetoolBtn = QtGui.QPushButton("Pick section (two clicks)")
        self.linetoolBtn.clicked.connect(self.activateLineTool)
        self.linetoolBtn.setEnabled(False)
        ls.addRow(self.linetoolBtn)
        self.p1label = QtGui.QLabel("")
        self.p2label = QtGui.QLabel("")
        ls.addRow(QtGui.QLabel("Point 1:"), self.p1label)
        ls.addRow(QtGui.QLabel("Point 2:"), self.p2label)
        self.runSecBtnSimple = QtGui.QPushButton("Create section")
        self.runSecBtnSimple.clicked.connect(self.ltool.runsec)
        self.runSecBtnSimple.setEnabled(False)
        ls.addRow(self.runSecBtnSimple)
        self.simple_widget.setLayout(ls)
        ### ADVANCED ###
        lo = QtGui.QFormLayout()
        ######
        lo.addRow(QtGui.QLabel("Step 1. Choose point cloud and visualize it:"))
        self.txtinfile = QpalsDropTextbox.QpalsDropTextbox(layerlist=self.layerlist)
        lo.addRow(QtGui.QLabel("Input file (odm)"), self.txtinfile)
        self.runShdBtn = QtGui.QPushButton("Create shading")
        self.runShdBtn.clicked.connect(self.loadShading)
        lo.addRow(self.runShdBtn)
        ######
        self.status = QtGui.QListWidgetItem("hidden status")
        lo.addRow(QtGui.QLabel("Step 2. Create sections"))
        self.secInst = QpalsModuleBase.QpalsModuleBase(execName=os.path.join(self.project.opalspath, "opalsSection.exe"), QpalsProject=self.project)
        self.secInst.load()
        self.secInst.listitem = self.status
        secUi = self.secInst.getParamUi()
        lo.addRow(secUi)

        self.runSecBtn = QtGui.QPushButton("Calculate sections")
        self.runSecBtn.clicked.connect(self.runSection)
        lo.addRow(self.runSecBtn)
        #######
        lo.addRow(QtGui.QLabel("Step 3. Use the Section picking tool to show Sections"))
        self.pickSecBtn = QtGui.QPushButton("Pick section")
        self.pickSecBtn.clicked.connect(self.activateTool)
        lo.addRow(self.pickSecBtn)

        self.advanced_widget.setLayout(lo)
        self.tabs.addTab(self.simple_widget, "Simple")
        self.tabs.addTab(self.advanced_widget, "Advanced")
        return self.tabs

    def loadShading(self):
        self.runShdBtn.setEnabled(False)
        self.runShdBtn.setText("Calculating shading...")
        showfile = QpalsShowFile.QpalsShowFile(self.project.iface, self.layerlist, self.project)
        showfile.curVisMethod = QpalsShowFile.QpalsShowFile.METHOD_SHADING
        showfile.cellSizeBox = QtGui.QLineEdit("1")
        self.visLayer = showfile.load(infile_s=[self.txtinfile.text(), self.txtinfileSimple.text()])
        self.runShdBtn.setText("Create shading")
        self.runShdBtn.setEnabled(True)
        self.linetoolBtn.setEnabled(True)


    def runSection(self):
        outParamFileH = tempfile.NamedTemporaryFile(delete=False)
        outParamFile = outParamFileH.name
        outParamFileH.close()
        self.runSecBtn.setEnabled(False)
        self.runSecBtn.setText("Calculating sections...")
        outParamFileParam = QpalsParameter.QpalsParameter('outParamFile', outParamFile, None, None, None, None, None)
        self.secInst.params.append(outParamFileParam)
        self.secInst.run()
        self.secInst.params.remove(outParamFileParam)
        dom = minidom.parse(outParamFile)
        parameters = dom.getElementsByTagName("Parameter")
        outGeoms = []
        for param in parameters:
            if param.attributes["Name"].value == "outGeometry":
                for val in param.getElementsByTagName("Val"):
                    outGeoms.append(val.firstChild.nodeValue) # contains WKT for one section
        dom.unlink()

        self.secLayer = self.iface.addVectorLayer("Polygon", "Sections", "memory")
        pr = self.secLayer.dataProvider()
        featcnt = 1
        for outGeom in outGeoms:
            obj = ogr.CreateGeometryFromWkt(outGeom)
            geometrycnt = obj.GetGeometryCount()
            centersec = obj.GetGeometryRef(0)
            box = obj.GetGeometryRef(1)
            origin = obj.GetGeometryRef(2)
            pointcloud = obj.GetGeometryRef(3)

            feat = QgsFeature(featcnt)
            points = []
            ring = box.GetGeometryRef(0)
            for i in range(ring.GetPointCount()):
                pt = ring.GetPoint(i)
                points.append(QgsPoint(pt[0], pt[1]))
            feat.setGeometry(QgsGeometry.fromPolygon([points]))
            pr.addFeatures([feat])
            self.sections[featcnt] = {'wkt': pointcloud.ExportToWkt(),
                                      'name': origin.GetY()}
            if geometrycnt > 4:
                attrcloud = obj.GetGeometryRef(4)
                self.sections[featcnt]['attr_wkt'] = attrcloud.ExportToWkt()

            featcnt += 1

        self.secLayer.updateExtents()
        self.secLayer.setCustomProperty("qpals-odmpath", "section")
        self.secLayer.setLayerTransparency(50)
        QgsMapLayerRegistry.instance().addMapLayer(self.secLayer)
        self.iface.mapCanvas().refresh()

        self.runSecBtn.setText("Calculate sections")
        self.runSecBtn.setEnabled(True)

    def activateTool(self):
        self.secLayer.removeSelection()
        tool = PointTool(self.iface.mapCanvas(), self.secLayer, self.sections)
        self.iface.mapCanvas().setMapTool(tool)

    def activateLineTool(self):
        self.iface.mapCanvas().setMapTool(self.ltool)

class LineTool(QgsMapTool):
    def __init__(self, canvas, layer, secInst):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.visLayer = None
        self.secInst = secInst
        self.p1 = None
        self.p2 = None
        self.seclength = 0
        self.midpoint = None
        self.ab0N = None

    def canvasPressEvent(self, event):
        pass

    def canvasMoveEvent(self, event):
        pass

    def canvasReleaseEvent(self, event):


        layerPoint = self.toLayerCoordinates(self.layer, event.pos())
        if self.p1 and not self.p2:
            self.p2 = layerPoint
            self.secInst.p2label.setText(str(layerPoint))
            self.secInst.runSecBtnSimple.setEnabled(True)

            self.visLayer = self.secInst.iface.addVectorLayer("Polygon", "Sections", "memory")
            pr = self.visLayer.dataProvider()
            feat = QgsFeature()
            a = np.array([self.p1.x(), self.p1.y()])
            b = np.array([self.p2.x(), self.p2.y()])
            ab = b-a
            self.seclength = np.linalg.norm(ab)
            self.midpoint = a + ab/2
            ab0 = ab/self.seclength
            self.ab0N = np.array([-ab0[1], ab0[0]])

            c1 = a + float(self.secInst.txtthickness.text())/2*self.ab0N
            c2 = b + float(self.secInst.txtthickness.text())/2*self.ab0N
            c3 = b - float(self.secInst.txtthickness.text())/2*self.ab0N
            c4 = a - float(self.secInst.txtthickness.text())/2*self.ab0N
            points = [QgsPoint(c1[0], c1[1]),
                      QgsPoint(c2[0], c2[1]),
                      QgsPoint(c3[0], c3[1]),
                      QgsPoint(c4[0], c4[1])
                      ]

            feat.setGeometry(QgsGeometry.fromPolygon([points]))
            pr.addFeatures([feat])

            self.visLayer.setLayerTransparency(50)
            QgsMapLayerRegistry.instance().addMapLayer(self.visLayer)
            self.secInst.iface.mapCanvas().refresh()
        else:
            self.p1 = layerPoint
            self.secInst.p1label.setText(str(layerPoint))
            self.p2 = None
            self.secInst.p2label.setText("")
            self.secInst.runSecBtnSimple.setEnabled(False)
            if self.visLayer:
                QgsMapLayerRegistry.instance().removeMapLayer(self.visLayer.id())

    def runsec(self):
        #write polyline shp to file
        outShapeFileH = tempfile.NamedTemporaryFile(delete=False)
        outShapeFile = outShapeFileH.name
        outShapeFileH.close()
        print outShapeFile
        driver = ogr.GetDriverByName("ESRI Shapefile")
        data_source = driver.CreateDataSource(outShapeFile + ".shp")
        layer = data_source.CreateLayer("", None, ogr.wkbLineString)
        layer.CreateField(ogr.FieldDefn("ID", ogr.OFTInteger))
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("ID", 0)
        line = ogr.Geometry(ogr.wkbLineString)
        line.AddPoint(self.midpoint[0], self.midpoint[1])
        nextpoint = self.midpoint + self.ab0N
        line.AddPoint(nextpoint[0], nextpoint[1])
        feature.SetGeometry(line)
        feature.Destroy()
        data_source.Destroy()
        #run section
        Module = QpalsModuleBase.QpalsModuleBase(execName=os.path.join(self.secInst.project.opalspath, "opalsSection.exe"), QpalsProject=self.secInst.project)
        #read from file and display

    def activate(self):
        pass

    def deactivate(self):
        pass

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

class PointTool(QgsMapTool):
    def __init__(self, canvas, layer, sections):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.sections = sections

    def canvasPressEvent(self, event):
        pass

    def canvasMoveEvent(self, event):
        pass

    def canvasReleaseEvent(self, event):
        if self.sections:
            layerPoint = self.toLayerCoordinates(self.layer, event.pos())

            shortestDistance = float("inf")
            closestFeatureId = -1

            # Loop through all features in the layer
            for f in self.layer.getFeatures():
                dist = f.geometry().distance(QgsGeometry.fromPoint(layerPoint))
                if dist < shortestDistance:
                    shortestDistance = dist
                    closestFeatureId = f.id()

            self.layer.select(closestFeatureId)

            # parse wkt
            pointcloud = ogr.CreateGeometryFromWkt(self.sections[closestFeatureId]['wkt'])
            xvec = []
            yvec = []
            zvec = []

            attrcloud = None
            cvec = []

            if 'attr_wkt' in self.sections[closestFeatureId]:
                attrcloud = ogr.CreateGeometryFromWkt(self.sections[closestFeatureId]['attr_wkt'])

            for i in range(pointcloud.GetGeometryCount()):
                pt = pointcloud.GetGeometryRef(i)
                xvec.append(pt.GetX())
                yvec.append(pt.GetY())
                zvec.append(pt.GetZ())
                if attrcloud:
                    at = attrcloud.GetGeometryRef(i)
                    cvec.append(at.GetZ())

            if attrcloud:
                plt.scatter(x = xvec, y = zvec, c = cvec, cmap='summer')
                plt.colorbar()
            else:
                plt.scatter(xvec,zvec)
            plt.title("Section %.1f" %self.sections[closestFeatureId]['name'])
            plt.xlabel("Distance from Axis")
            plt.ylabel("Height")
            plt.show()

    def activate(self):
        pass

    def deactivate(self):
        pass

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True