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

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from openmolar.qt4gui import resources_rc


class ChainLabel(QtWidgets.QLabel):

    '''
    a custom label with a chain link
    '''
    toggled = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        QtWidgets.QLabel.__init__(self, parent)
        self.chainpic = QtGui.QPixmap(":/icons/chain.png")
        self.unchainpic = QtGui.QPixmap(":/icons/chain-broken.png")
        self.setFixedWidth(30)
        self._chained = True
        self._update()

    def mousePressEvent(self, event):
        self._chained = not self._chained
        self._update()

    def setValue(self, chained):
        self._chained = chained
        self._update()

    def _update(self):
        if self._chained:
            self.setPixmap(self.chainpic)
        else:
            self.setPixmap(self.unchainpic)
        self.toggled.emit(self._chained)


if __name__ == "__main__":
    def test(arg):
        print(("chained = %s" % arg))

    import sys
    app = QtWidgets.QApplication(sys.argv)
    widg = ChainLabel()
    widg.setMinimumSize(QtCore.QSize(100, 100))
    widg.toggled.connect(test)

    widg.show()
    sys.exit(app.exec_())
