#! /usr/bin/python

# ########################################################################### #
# #                                                                         # #
# # Copyright (c) 2009-2016 Neil Wallace <neil@openmolar.com>               # #
# #                                                                         # #
# # This file is part of OpenMolar.                                         # #
# #                                                                         # #
# # OpenMolar is free software: you can redistribute it and/or modify       # #
# # it under the terms of the GNU General Public License as published by    # #
# # the Free Software Foundation, either version 3 of the License, or       # #
# # (at your option) any later version.                                     # #
# #                                                                         # #
# # OpenMolar is distributed in the hope that it will be useful,            # #
# # but WITHOUT ANY WARRANTY; without even the implied warranty of          # #
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           # #
# # GNU General Public License for more details.                            # #
# #                                                                         # #
# # You should have received a copy of the GNU General Public License       # #
# # along with OpenMolar.  If not, see <http://www.gnu.org/licenses/>.      # #
# #                                                                         # #
# ########################################################################### #

import gettext
import logging
import sys
import traceback

from PyQt5 import QtCore
from PyQt5 import QtWidgets

from lib_om_chart.restorable_app import RestorableApplication
from lib_om_chart.chart_widget import ChartWidget
from lib_om_chart.patient import Patient, PatientNotFoundException
from lib_om_chart.config import SURGERY_NO
from lib_om_chart.config_dialog import ConfigDialog
from lib_om_chart.connect import Connection

LOGGER = logging.getLogger("om_chart")


class MainWindow(QtWidgets.QMainWindow):
    connection = Connection()
    _loaded_serialno = None

    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        if not self.connection.is_configured:
            self.configure()

        self.setWindowTitle("Dental Chart Viewer")
        self.chart_widget = ChartWidget(self)
        self.setCentralWidget(self.chart_widget)

        menu_file = QtWidgets.QMenu(_("&File"), self)
        load_action = QtWidgets.QAction("&Load", self)
        quit_action = QtWidgets.QAction("&Quit", self)
        reload_action = QtWidgets.QAction("&Reload", self)

        reconfigure_action = QtWidgets.QAction("Re&configure", self)

        menu_file.addAction(load_action)
        menu_file.addAction(quit_action)

        self.menuBar().addMenu(menu_file)
        self.menuBar().addAction(reload_action)
        self.menuBar().addAction(reconfigure_action)

        load_action.triggered.connect(self.get_patient)
        reload_action.triggered.connect(self.reload_patient)
        reconfigure_action.triggered.connect(self.check_reconfigure)
        quit_action.triggered.connect(
            QtWidgets.QApplication.instance().closeAllWindows)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self.check_record_in_use)
        self.timer.start()

    def sizeHint(self):
        return QtCore.QSize(800, 200)

    def loadSettings(self):
        '''
        load settings from QtCore.QSettings.
        '''
        settings = QtCore.QSettings()
        # Qt settings
        self.restoreGeometry(settings.value("geometry").toByteArray())
        self.restoreState(settings.value("windowState").toByteArray())

    def saveSettings(self):
        '''
        save settings from QtCore.QSettings
        '''
        settings = QtCore.QSettings()
        # Qt settings
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def closeEvent(self, event=None):
        '''
        re-implement the close event of QtWidgets.QMainWindow, and check the user
        really meant to do this.
        '''
        self.timer.stop()
        result = QtWidgets.QMessageBox.question(
            self, _("Confirm"),
            _("Quit Application?"),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok

        if result:
            self.saveSettings()
        else:
            self.timer.start()
            event.ignore()

    @property
    def max_sno(self):
        '''
        TODO - poll the database for this value.
        '''
        db = self.connection.connection
        cursor = db.cursor()
        cursor.execute("select max(serialno) from patients")
        row = cursor.fetchone()
        return row[0] + 10  # allow for a few new patients.

    def get_patient(self):
        sno, result = QtWidgets.QInputDialog.getInt(self,
                                                _("Manual Select"),
                                                _("Select a serialno to load"),
                                                1, 1, self.max_sno)

        if result:
            self.load_patient(sno)

    def load_patient(self, sno):
        '''
        load the data for patient with this serialno
        '''
        self.chart_widget.clear()

        QtWidgets.QApplication.instance().setOverrideCursor(
            QtCore.Qt.WaitCursor)
        logging.debug("loading patient %s", sno)
        try:
            pt = Patient(sno, self.connection.connection)

            self.chart_widget.chartgrid = pt.chartgrid()

            for tooth in pt.TOOTH_FIELDS:
                static_text = pt.__dict__[tooth]
                if static_text:
                    self.chart_widget.setToothProps(tooth, static_text)

        except PatientNotFoundException:
            self._message_box = QtWidgets.QMessageBox(self)
            self._message_box.setText("Patient Serialno %s not found!" % sno)
            self._message_box.setIcon(self._message_box.Warning)
            self._message_box.setWindowTitle("whoops")
            self._message_box.show()
            QtCore.QTimer.singleShot(1000, self._message_box.hide)

        self.chart_widget.update()

        QtWidgets.QApplication.instance().restoreOverrideCursor()

    def reload_patient(self):
        LOGGER.debug("reloading patient")
        if self._loaded_serialno:
            self.load_patient(self._loaded_serialno)
        else:
            self.check_record_in_use()

    def check_reconfigure(self):
        if QtWidgets.QMessageBox.question(
                self, _("confirm"),
                _("Do you really want to reconfigure this application?"),
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok:
            self.reconfigure()

    def configure(self):
        self.reconfigure(reconfigure=False)

    def reconfigure(self, reconfigure=True):
        dl = ConfigDialog(self)
        if reconfigure:
            dl.load_config()
        if dl.exec_(True):
            dl.write_config()
            self.connection.reload()
        if reconfigure:
            self.reload_patient()

    def excepthook(self, exc_type, exc_val, tracebackobj):
        '''
        PyQt5 prints unhandled exceptions to stdout and carries on regardless
        I don't want this to happen.
        so sys.excepthook is passed to this
        '''
        self.timer.stop()
        QtWidgets.QApplication.instance().restoreOverrideCursor()
        message = ""
        for l in traceback.format_exception(exc_type, exc_val, tracebackobj):
            message += l
        QtWidgets.QMessageBox.warning(
            self, _("Error"),
            'UNHANDLED EXCEPTION!<hr /><pre>%s</pre>' % message)
        LOGGER.warning(message)
        self.timer.start()

    def check_record_in_use(self):
        if not SURGERY_NO:
            return
        logging.debug("checking record in use")
        db = self.connection.connection
        cursor = db.cursor()
        cursor.execute(
            "select serialno from calldurr where stn = %s", (SURGERY_NO,))
        row = cursor.fetchone()
        if row:
            serialno = row[0]
            if serialno and serialno != self._loaded_serialno:
                self.load_patient(serialno)
                self._loaded_serialno = serialno
                # self.setWindowState(
                #    QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
                self.activateWindow()


if __name__ == "__main__":
    gettext.install("openmolar")
    logging.basicConfig(level=logging.DEBUG)
    app = RestorableApplication("om_charter")
    mw = MainWindow()
    sys.excepthook = mw.excepthook
    mw.show()
    app.exec_()
