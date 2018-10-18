# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgis_project2kmz
                                 A QGIS plugin
 A quick & dirty plugin to build a kmz from a layer of spatial points
                             -------------------
        begin                : 2018-06-22
        copyright            : (C) 2016 by Pedro Tarroso (C) 2018 by ARGaeta/Vertical Srl
        email                : ptarroso@cibio.up.pt ar_gaeta@yahoo.it
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; version 2 of the License.               *
 *                                                                         *
 ***************************************************************************/
"""


'''
OTTIMIZZAZIONI:

- Esporto UN kmz per OGNI layer nel percorso del progeto salvato. Se il progetto non e' salvato, salvo nella HOME dell'utente -- OK
- Esporta solo i layer ACCESI -- OK
- Esporta tutte le categorie o solo quelle accese com'e' tuttora?
- Al momento esporto solo se e' categorizzato. Quali campi prendere difatti per creare le folder altrimenti?


'''



from PyQt4.QtCore import *
#from PyQt4.QtGui import QAction, QIcon, QColor
from PyQt4.QtGui import *
from qgis.gui import QgsMapCanvas, QgsMapCanvasLayer
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from layer2kmz_dialog import layer2kmzDialog
import os
import tempfile
import zipfile
from kml import kml

#importo altre librerie prese dal plugin pgrouting
import pgRoutingLayer_utils as Utils

class layer2kmz:
    """QGIS Plugin Implementation."""
    
    epsg_srid = 0
    xform = None  # regola di trasformazione dello srid

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'layer2kmz_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = layer2kmzDialog(iface)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&layer2kmz')
        # TODO: We are going to let the user set this up in a future iteration
        if self.iface.pluginToolBar():
            self.toolbar = self.iface.pluginToolBar()
        else:
            self.toolbar = self.iface.addToolBar(u'layer2kmz')
        self.toolbar.setObjectName(u'layer2kmz')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('layer2kmz', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/qgis_project2kmz/qgis_project2kmz.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Project to KMZ'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&layer2kmz'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""

        global epsg_srid
        global xform
        
        # Update combos
        layers = self.iface.legendInterface().layers()
        ## show all vector layers in combobox
        allLayers = [lyr for lyr in layers if lyr.type() == 0]
        #self.dlg.updateLayerCombo([lyr.name() for lyr in allLayers])

        # show the dialog
        #self.dlg.show()
        # Run the dialog event loop
        #result = self.dlg.exec_()
        result = 1 #gli faccio saltare questa parte di visualizzazione della maschera
        
        # See if OK was pressed
        if result:
            #layerName = self.dlg.getVectorLayer()
            #labelFld = self.dlg.getLabel()
            #folderFld = self.dlg.getFolder()
            #exportFld = self.dlg.getExports()
            #outFile = self.dlg.getOutFile()
            
            '''
            #IMPONGO questi valori:
            layerName = 'ebw_location'
            labelFld = 'NOME'
            folderFld = 'TIPO'
            exportFld = ['ID', 'NOME', 'TIPO', 'INDIRIZZO', 'CIVICO', 'NOTE']
            #Utils.logMessage('Campi da esportare ' + str(exportFld) + ' - Tipo ' + str(type(exportFld)))
            outFile = os.getenv("HOME") + '\da_qgis_project2kmz_con_reproject.kmz'
            Utils.logMessage('Percorso di salvataggio: ' + str(outFile))
            '''

            # Get the layer object from active layers
            canvas = self.iface.mapCanvas()
            shownLayers_name = [x.name() for x in canvas.layers()] #ELENCO DEI LAYER ATTIVI
            shownLayers = [x for x in canvas.layers()] #ELENCO DEI LAYER ATTIVI
            #layer = canvas.layer(shownLayers_name.index(layerName))

            '''
            if layerName not in shownLayers_name:
                self.dlg.warnMsg("Species table not found or active!", layerName)
            elif outFile == "":
                self.dlg.errorMsg("Choose an output kmz file!", "")

            elif exportFld== []:
                self.dlg.errorMsg("At least one field to export must be selected.", "")
            else:
                self.dlg.setProgressBar("Processing", "", 100)

                kmlproc = kmlprocess(layer, labelFld, folderFld, exportFld,
                                  outFile, self.dlg.ProgressBar)
                kmlproc.process()
            '''
            
            #Considerando un export diretto senza maschera passo ssubito alla sessione successiva senza controlli
            #Per salvare tutti i layer ATTIVI del progetto:
            for singlelayer in shownLayers:
                Utils.logMessage(singlelayer.name())
                crs = singlelayer.crs()
                epsg_srid = int(crs.postgisSrid())
                self.epsg_srid = epsg_srid
                Utils.logMessage(str(epsg_srid))
                
                # Definisco regole di trasformazione dello srid in 4326
                crsDest = QgsCoordinateReferenceSystem(4326)
                crsSrc = QgsCoordinateReferenceSystem(epsg_srid)
                xform = QgsCoordinateTransform(crsSrc, crsDest)
                self.xform = xform
                
                #IMPONGO questi valori:
                #layerName = 'ebw_location'
                layerName = singlelayer.name()
                labelFld = 'NOME'
                folderFld = 'TIPO'
                exportFld = ['ID', 'NOME', 'TIPO', 'INDIRIZZO', 'CIVICO', 'NOTE']
                
                # provo prima a salvare il file nello stesso percorso del progetto:
                prjfi = QFileInfo(QgsProject.instance().fileName())
                outFile = os.getenv("HOME") + '\qgis_project2kmz_' + str(layerName) + '.kmz'
                if (prjfi.absolutePath()):
                    outFile = prjfi.absolutePath() + '\qgis_project2kmz_' + str(layerName) + '.kmz'
                Utils.logMessage('Percorso di salvataggio: ' + str(outFile))
                
                #Alcuni valori li posso prelevare dinamicamente dal progetto.
                # Il campo di STILE:
                rnd_field = singlelayer.rendererV2()
                if rnd_field.type() == u'categorizedSymbol':
                    styleField = rnd_field.classAttribute()
                    folderFld = styleField
                    labelFld = styleField #per il momento il LABEL e' uguale al campo dello stile
                else:
                    continue #per il momento NON esporto layer con stile non categorizzato
            
                # TUTTI i CAMPI del layer:
                exportFld = [field.name() for field in singlelayer.pendingFields() ]
                
                
                #return 0
                #Per OGNI layer ATTIVO esporto un KMZ
                self.dlg.setProgressBar("Processing", "", 100)
                kmlproc = kmlprocess(singlelayer, labelFld, folderFld, exportFld, outFile, self.dlg.ProgressBar, xform)
                kmlproc.process()
            

def conv2str(x):
    ## Converts the input to string, avoiding unicode errors
    try:
        cv = str(x)
    except UnicodeEncodeError:
        cv = x #.encode("ascii", "xmlcharrefreplace")
    return(cv)

def argb2abgr(col):
    #KML format: AlphaBGR instead of AlphaRGB
    return(col[0:2] + col[6:8] + col[4:6] + col[2:4])


class kmlprocess():
    def __init__(self, layer, label, folder, exports, outFile, prg, xf):
        self.layer = layer
        self.label = label
        self.folder = folder
        self.exports = exports
        self.styleField = None
        self.outFile = outFile
        self.tmpDir = tempfile.gettempdir()
        self.progress = prg
        self.totalCounter = 1
        self.counter = 0
        self.xf = xf

    def processLayer(self):
        lyr = self.layer
        ## Sets the total counter for updating progress
        self.totalCounter = lyr.featureCount() * 2

        lyrFields = [f.name() for f in lyr.pendingFields()]
        expFieldInd = [lyrFields.index(f) for f in self.exports]
        featIter = lyr.getFeatures()
        fldInd = lyrFields.index(self.folder)
        lblInd = lyrFields.index(self.label)

        ## If there is a style field, save a list of style for each feature
        if self.styleField is not None:
            styles = []
            styInd = lyrFields.index(self.styleField)

        ## Process all features
        data = []
        featFolder = []
        coords = []
        labels = []

        feats = []
        
        for feature in featIter:
            self.updateProgress()

            # Converto ogni singola geometria nello srid 4326
            g = feature.geometry()
            g.transform(self.xf)
            feature.setGeometry(g) #forse gia' questo step mi converte la feature in 4326, dunque feats non mi serve...verifica!
            feats.append(feature)
            
            fGeo = feature.geometry().type()

            if self.styleField is not None:
                styleFeat = conv2str(feature.attributes()[styInd])

            # Export only features that have active styles (displayed on the map)
            if (self.styleField is None or styleFeat in self.getStylesNames()):
                # note: converting everything to string!
                data.append([conv2str(feature.attributes()[i]) for i in expFieldInd])
                featFolder.append(conv2str(feature.attributes()[fldInd]))
                labels.append(conv2str(feature.attributes()[lblInd]))
                if fGeo == 0: # Point case
                    crd = tuple(feature.geometry().asPoint())
                elif fGeo == 1: # Line case
                    crd = feature.geometry().asPolyline()
                    crd = [tuple(x) for x in crd]
                elif fGeo == 2: # Polygon case
                    crd = feature.geometry().asPolygon()
                    crd = [[tuple(x) for x in y] for y in crd]
                coords.append(crd)
                if self.styleField is not None:
                    styles.append(styleFeat)
            else:
                self.totalCounter -= 1

            self.counter += 1

        self.coords = coords
        self.data = data
        self.featFolder = featFolder
        self.labels = labels
        if self.styleField is not None:
            self.featStyles = styles

    def setStyles(self):
        lyr = self.layer
        lyrGeo = lyr.geometryType()
        rnd = lyr.rendererV2()
        styles = []
        if rnd.type() == u'categorizedSymbol':
            styleField = rnd.classAttribute()
            self.styleField = styleField
            Utils.logMessage('Campo dello stile categorizzato: ' + str(styleField))
            for cat in rnd.categories():
                name = conv2str(cat.value())
                symb = cat.symbol()
                if cat.renderState():
                    if lyrGeo == 0: ## Point case
                        imgname = "color_%s.png" % name
                        symb.exportImage(os.path.join(self.tmpDir, imgname),
                                         "png", QSize(30, 30))
                        styles.append([name, {"iconfile": imgname}])
                    elif lyrGeo == 1: ## Line case
                        color = "%x" % symb.color().rgba()
                        width = symb.width()
                        styles.append([name, {"color": color, "width": width}])
                    elif lyrGeo == 2: ## Polygon case
                        symbLyr = symb.symbolLayer(0) # Get only first symbol layer
                        fill = argb2abgr("%x" % symbLyr.color().rgba())
                        border = argb2abgr("%x" % symbLyr.borderColor().rgba())
                        outline = symbLyr.borderWidth()
                        styles.append([name, {"fill": fill,
                                              "outline": outline,
                                               "border": border}])
        elif rnd.type() == u'singleSymbol':
            symb = rnd.symbol()
            if lyrGeo == 0: ## Point case
                imgname = "color_style.png"
                symb.exportImage(os.path.join(self.tmpDir, imgname), "png",
                                 QSize(30, 30))
                styles.append(["style", {"iconfile": imgname}])
            elif lyrGeo == 1: ## Line case
                color = "%x" % symb.color().rgba()
                width = symb.width()
                styles.append(["style", {"color": color, "width": width}])
            elif lyrGeo == 2: ## Polygon case
                symbLyr = symb.symbolLayer(0) # Get only first symbol layer
                fill = argb2abgr("%x" % symbLyr.color().rgba())
                border = argb2abgr("%x" % symbLyr.borderColor().rgba())
                outline = symbLyr.borderWidth()
                styles.append(["style", {"fill": fill,
                                         "outline": outline,
                                         "border": border}])
        else:
            self.error.emit("Symbology must be single or categorized.")
            self.finished.emit(False)

        self.styles = styles

    def getStylesNames(self):
        if hasattr(self, 'styles'):
            return([x[0] for x in self.styles])

    def updateProgress(self):
        progress = int(self.counter / float(self.totalCounter) * 100)
        self.progress(progress)

    def cleanup(self):
        ## Removes the temporary files created
        for style in self.styles:
            if "iconfile" in style[1]:
                os.remove(os.path.join(self.tmpDir, style[1]["iconfile"]))
        os.remove(os.path.join(self.tmpDir, "doc.kml"))

    def process(self):
        self.setStyles()
        self.processLayer()
        Kml = kml(self.layer.name())
        types = ["string" for x in self.exports]
        Kml.addSchema(self.layer.name(), self.exports, types)

        for item in self.styles:
            styId, kwargs = item
            Kml.addStyle(styId, **kwargs)

        msg = QMessageBox()
        if not self.styles:
            #self.error.emit("La simbologia deve essere categorizzata e almeno UNA categoria deve essere accesa.")
            #self.finished.emit(False)
            msg.setText("La simbologia deve essere categorizzata e almeno UNA categoria deve essere accesa. Il layer %s non verra' esportato" % (self.layer.name()))
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Layer non esportabile!")
            msg.setStandardButtons(QMessageBox.Ok)
            retval = msg.exec_()
            Utils.logMessage("La simbologia deve essere categorizzata e almeno UNA categoria deve essere accesa.")
            return 0
        style = self.styles[0][0]
        for i in range(len(self.data)):
            self.updateProgress()
            folder = self.featFolder[i]
            name = self.labels[i]
            coords = self.coords[i]
            if self.styleField is not None:
                style = self.featStyles[i]
            fields = {}
            fields[self.layer.name()] = zip(self.exports, self.data[i])
            Kml.addPlacemark(folder, name, style, coords, fields)
            self.counter += 1

        tmpKml = os.path.join(self.tmpDir, "doc.kml")
        fstream = open(tmpKml, "w")
        fstream.writelines(Kml.generatekml())
        fstream.close()

        z = zipfile.ZipFile(self.outFile, "w")
        z.write(tmpKml, arcname="doc.kml")
        for styDict in [x[1] for x in self.styles]:
            if "iconfile" in styDict.keys():
                filename = os.path.join(self.tmpDir, styDict["iconfile"])
                z.write(filename, arcname=os.path.basename(filename))
        z.close()

        self.cleanup()
        self.updateProgress()
