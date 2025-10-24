import sys
import os
import yt_dlp
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QComboBox, 
                             QLabel, QFileDialog, QProgressBar, QMessageBox,
                             QFrame, QScrollArea, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, bool)
    error = pyqtSignal(str)

    def __init__(self, url, quality, output_path):
        super().__init__()
        self.url = url
        self.quality = quality
        self.output_path = output_path
        self.is_cancelled = False

    def run(self):
        try:
            # Map quality to format selection
            format_map = {
                '360p': 'best[height<=360]',
                '480p': 'best[height<=480]',
                '720p': 'best[height>=720]',
                'Best Available': 'best'
            }
            
            ydl_opts = {
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'format': format_map.get(self.quality, 'best'),
                'noplaylist': True,
                'quiet': True,
                'no_warnings': False,
                'progress_hooks': [self.progress_hook],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
                
            if not self.is_cancelled:
                self.finished.emit(self.url, True)
                
        except Exception as e:
            if not self.is_cancelled:
                self.error.emit(str(e))

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = int(float(d['downloaded_bytes']) / float(d['total_bytes']) * 100)
                self.progress.emit(percent)
            elif 'downloaded_bytes' in d and d.get('total_bytes_estimate'):
                percent = int(float(d['downloaded_bytes']) / float(d['total_bytes_estimate']) * 100)
                self.progress.emit(percent)
        elif d['status'] == 'finished':
            self.progress.emit(100)

    def cancel(self):
        self.is_cancelled = True


class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_threads = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('YouTube Video Downloader')
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #3c3c3c;
                color: #fff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #6bb5ff;
            }
            QTextEdit, QComboBox, QPushButton, QLabel {
                font-size: 12px;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #3c3c3c;
                color: #fff;
                border: 1px solid #555;
                padding: 5px;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #fff;
                border: 1px solid #555;
                padding: 5px;
                min-width: 100px;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #fff;
                selection-background-color: #6bb5ff;
            }
            QPushButton {
                background-color: #6bb5ff;
                color: #fff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5aa0e6;
            }
            QPushButton:pressed {
                background-color: #4a8bcb;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
            QLabel {
                color: #fff;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                background-color: #3c3c3c;
                color: #fff;
            }
            QProgressBar::chunk {
                background-color: #6bb5ff;
                width: 10px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Input group
        input_group = QGroupBox("Video URLs")
        input_layout = QVBoxLayout()
        
        self.url_textedit = QTextEdit()
        self.url_textedit.setPlaceholderText("Enter YouTube URLs (one per line)")
        input_layout.addWidget(self.url_textedit)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Settings group
        settings_group = QGroupBox("Download Settings")
        settings_layout = QHBoxLayout()
        
        # Quality selection
        quality_layout = QVBoxLayout()
        quality_label = QLabel("Video Quality:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["360p", "480p", "720p", "Best Available"])
        self.quality_combo.setCurrentIndex(2)  # Default to 720p
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        settings_layout.addLayout(quality_layout)
        
        # Path selection
        path_layout = QVBoxLayout()
        path_label = QLabel("Download Path:")
        path_selector_layout = QHBoxLayout()
        self.path_label = QLabel(os.path.expanduser("~/Downloads"))
        self.path_label.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.path_label.setStyleSheet("background-color: #3c3c3c; color: #fff; padding: 5px;")
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_path)
        path_selector_layout.addWidget(self.path_label)
        path_selector_layout.addWidget(self.browse_button)
        path_layout.addWidget(path_label)
        path_layout.addLayout(path_selector_layout)
        settings_layout.addLayout(path_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Progress group
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout()
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.progress_widget = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_widget)
        self.scroll_area.setWidget(self.progress_widget)
        
        progress_layout.addWidget(self.scroll_area)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Action buttons
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Start Download")
        self.download_button.clicked.connect(self.start_download)
        self.cancel_button = QPushButton("Cancel All")
        self.cancel_button.clicked.connect(self.cancel_all)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.path_label.text())
        if path:
            self.path_label.setText(path)

    def start_download(self):
        urls = self.url_textedit.toPlainText().strip().split('\n')
        if not urls or not urls[0]:
            QMessageBox.warning(self, "Input Error", "Please enter at least one YouTube URL")
            return
            
        quality = self.quality_combo.currentText()
        output_path = self.path_label.text()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        # Clear previous progress widgets
        for i in reversed(range(self.progress_layout.count())): 
            self.progress_layout.itemAt(i).widget().setParent(None)
        
        self.download_threads = []
        for url in urls:
            if url.strip():
                self.add_download_item(url.strip(), quality, output_path)
        
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def add_download_item(self, url, quality, output_path):
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet("QFrame { background-color: #3c3c3c; border-radius: 4px; }")
        layout = QHBoxLayout(frame)
        
        # URL label (shortened for display)
        display_url = url[:50] + "..." if len(url) > 50 else url
        url_label = QLabel(display_url)
        url_label.setToolTip(url)
        url_label.setStyleSheet("color: #fff;")
        url_label.setMinimumWidth(200)
        layout.addWidget(url_label)
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setValue(0)
        layout.addWidget(progress_bar)
        
        # Status label
        status_label = QLabel("Pending")
        status_label.setStyleSheet("color: #ffa500;")  # Orange for pending
        layout.addWidget(status_label)
        
        # Cancel button for individual download
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("QPushButton { background-color: #ff6b6b; } QPushButton:hover { background-color: #ff5252; }")
        layout.addWidget(cancel_button)
        
        self.progress_layout.addWidget(frame)
        
        # Create and start download thread
        thread = DownloadThread(url, quality, output_path)
        thread.progress.connect(progress_bar.setValue)
        thread.finished.connect(lambda url, success: self.download_finished(url, success, status_label, cancel_button))
        thread.error.connect(lambda error: self.download_error(url, error, status_label, cancel_button))
        
        cancel_button.clicked.connect(thread.cancel)
        
        self.download_threads.append(thread)
        thread.start()

    def download_finished(self, url, success, status_label, cancel_button):
        if success:
            status_label.setText("Completed")
            status_label.setStyleSheet("color: #4caf50;")  # Green for success
        else:
            status_label.setText("Cancelled")
            status_label.setStyleSheet("color: #ff6b6b;")  # Red for cancelled
        
        cancel_button.setEnabled(False)
        self.check_all_finished()

    def download_error(self, url, error, status_label, cancel_button):
        status_label.setText("Error")
        status_label.setStyleSheet("color: #ff6b6b;")  # Red for error
        status_label.setToolTip(error)
        cancel_button.setEnabled(False)
        self.check_all_finished()

    def check_all_finished(self):
        all_finished = all(not thread.isRunning() for thread in self.download_threads)
        if all_finished:
            self.download_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            
            # Show completion message
            completed = sum(1 for i in range(self.progress_layout.count()) 
                           if self.progress_layout.itemAt(i).widget().layout().itemAt(2).widget().text() == "Completed")
            total = self.progress_layout.count()
            
            if completed > 0:
                QMessageBox.information(self, "Download Complete", 
                                      f"Successfully downloaded {completed} of {total} videos.")

    def cancel_all(self):
        for thread in self.download_threads:
            thread.cancel()
        self.cancel_button.setEnabled(False)
        self.download_button.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern style
    
    # Set dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(43, 43, 43))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec_())