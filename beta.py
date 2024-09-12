import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, 
    QTabWidget, QMenuBar, QFileDialog, QMessageBox, QToolBar, QDialog, QFormLayout, QComboBox, 
    QDialogButtonBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QAction
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineDownloadRequest

SETTINGS_FILE = 'settings.json'

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        
        layout = QFormLayout()

        self.search_engine_box = QComboBox()
        self.search_engine_box.addItems(["Google", "Bing", "DuckDuckGo"])
        self.search_engine_box.setCurrentText(self.settings.get('search_engine', 'Google'))
        layout.addRow("Search Engine:", self.search_engine_box)

        self.http_warning_checkbox = QCheckBox()
        self.http_warning_checkbox.setChecked(self.settings.get('http_warning', True))
        layout.addRow("Warn before downloading from HTTP:", self.http_warning_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept(self):
        self.settings['search_engine'] = self.search_engine_box.currentText()
        self.settings['http_warning'] = self.http_warning_checkbox.isChecked()
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f)
        super().accept()

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Banana Browser')
        self.setGeometry(300, 150, 1200, 800)

        self.settings = self.load_settings()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.add_new_tab)
        self.tabs.currentChanged.connect(self.update_url_bar)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)

        self.setCentralWidget(self.tabs)
        self.statusBar()

        navtb = QToolBar("Navigation")
        self.addToolBar(navtb)

        back_btn = QPushButton('<')
        back_btn.clicked.connect(lambda: self.tabs.currentWidget().back())
        navtb.addWidget(back_btn)

        next_btn = QPushButton('>')
        next_btn.clicked.connect(lambda: self.tabs.currentWidget().forward())
        navtb.addWidget(next_btn)

        reload_btn = QPushButton('⟳')
        reload_btn.clicked.connect(lambda: self.tabs.currentWidget().reload())
        navtb.addWidget(reload_btn)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText('Type Url and press enter ...')
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navtb.addWidget(self.url_bar)

        new_tab_btn = QPushButton('+')
        new_tab_btn.clicked.connect(lambda: self.add_new_tab())
        navtb.addWidget(new_tab_btn)

        self.add_new_tab(QUrl('https://www.google.com'), 'New Tab')

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')

        new_tab_action = QAction('New Tab', self)
        new_tab_action.setShortcut('Ctrl+T')
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        file_menu.addAction(new_tab_action)

        open_file_action = QAction('Open File...', self)
        open_file_action.setShortcut('Ctrl+O')
        open_file_action.triggered.connect(self.open_file)
        file_menu.addAction(open_file_action)

        save_file_action = QAction('Save Page As...', self)
        save_file_action.setShortcut('Ctrl+S')
        save_file_action.triggered.connect(self.save_file)
        file_menu.addAction(save_file_action)

        print_action = QAction('Print...', self)
        print_action.setShortcut('Ctrl+P')
        print_action.triggered.connect(self.print_page)
        file_menu.addAction(print_action)

        settings_menu = menubar.addMenu('&Settings')
        settings_action = QAction('Settings', self)
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)

    def add_new_tab(self, qurl=None, label="New Tab"):
        if not isinstance(qurl, QUrl):
            qurl = QUrl(self.get_default_search_url())

        browser = CustomWebEngineView(self.settings)
        browser.setUrl(qurl)
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_url_bar(qurl))
        browser.loadFinished.connect(lambda _, i=i, browser=browser: self.tabs.setTabText(i, browser.page().title()))

    def update_url_bar(self, qurl):
        current_browser = self.tabs.currentWidget()
        if (qurl.scheme() != 'file'):
            if current_browser:
                self.url_bar.setText(qurl.toString())
                self.url_bar.setCursorPosition(0)

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith('http'):
            url = 'http://' + url
        self.tabs.currentWidget().setUrl(QUrl(url))

    def update_url_bar(self, index):
        qurl = self.tabs.currentWidget().url()
        self.url_bar.setText(qurl.toString())
        self.url_bar.setCursorPosition(0)

    def close_current_tab(self, i):
        if self.tabs.count() < 2:
            return
        self.tabs.removeTab(i)

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open file", "", "HTML files (*.htm *.html);;All files (*.*)")
        if filename:
            with open(filename, 'r') as f:
                html = f.read()
            self.tabs.currentWidget().setHtml(html)

    def save_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Page As", "", "HTML files (*.htm *.html);;All files (*.*)")
        if filename:
            self.tabs.currentWidget().page().save(filename)

    def print_page(self):
        QMessageBox.information(self, "Print", "Print functionality is not implemented yet.")

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.apply_settings()

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'search_engine': 'Google', 'http_warning': True}

    def apply_settings(self):
        pass

    def get_default_search_url(self):
        search_engine = self.settings.get('search_engine', 'Google')
        if search_engine == 'Google':
            return 'https://www.google.com'
        elif search_engine == 'Bing':
            return 'https://www.bing.com'
        elif search_engine == 'DuckDuckGo':
            return 'https://www.duckduckgo.com'

class CustomWebEngineView(QWebEngineView):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        profile.downloadRequested.connect(self.on_download_requested)

    def setUrl(self, qurl):
        super().setUrl(qurl)

    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        url = download_item.url().toString()

        # Überprüfe, ob die URL HTTP anstatt HTTPS verwendet
        if url.startswith("http://") and self.settings.get('http_warning', True):
            # Zeige eine Warnung an, dass die Verbindung unsicher ist
            warning = QMessageBox.warning(
                self,
                "Unsichere Verbindung",
                f"Die Datei wird von einer unsicheren HTTP-Seite heruntergeladen: {url}. Fortfahren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if warning == QMessageBox.StandardButton.No:
                download_item.cancel()
                return

        suggested_filename = download_item.suggestedFileName()
        path, _ = QFileDialog.getSaveFileName(self, "Save File", suggested_filename)
        if path:
            download_item.setDownloadDirectory(os.path.dirname(path))
            download_item.setDownloadFileName(os.path.basename(path))
            download_item.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    browser = Browser()
    browser.show()
    sys.exit(app.exec())
