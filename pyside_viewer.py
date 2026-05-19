import sys
import os
import json
import jwt
import requests

# Disable sandbox to fix Linux crash with QWebEngineView
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox)
from PySide6.QtWebEngineWidgets import QWebEngineView

API_URL = "http://localhost:5000/api/ocr/extract-html"
JWT_SECRET = "raas_jwt_secret_key"

class OCRViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Raas-OCR Viewer")
        self.resize(1200, 900)
        
        self.pages_html = []
        self.current_page_index = 0
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_upload = QPushButton("Upload Document")
        self.btn_upload.clicked.connect(self.upload_document)
        self.btn_upload.setMinimumWidth(150)
        self.btn_upload.setStyleSheet("padding: 8px; font-weight: bold;")
        
        from PySide6.QtWidgets import QLineEdit
        self.url_input = QLineEdit("http://localhost:8000/api/ocr/extract-html")
        self.url_input.setMinimumWidth(300)
        
        self.lbl_status = QLabel("Ready")
        
        self.btn_prev = QPushButton("Previous Page")
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_prev.setEnabled(False)
        self.btn_prev.setStyleSheet("padding: 8px;")
        
        self.btn_next = QPushButton("Next Page")
        self.btn_next.clicked.connect(self.next_page)
        self.btn_next.setEnabled(False)
        self.btn_next.setStyleSheet("padding: 8px;")
        
        self.lbl_page_info = QLabel("")
        self.lbl_page_info.setStyleSheet("font-weight: bold; margin: 0 10px;")
        
        toolbar.addWidget(self.btn_upload)
        toolbar.addWidget(self.url_input)
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_prev)
        toolbar.addWidget(self.lbl_page_info)
        toolbar.addWidget(self.btn_next)
        
        layout.addLayout(toolbar)
        
        # Web View
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

    def upload_document(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Document", "", "PDF or Images (*.pdf *.png *.jpg *.jpeg)")
        if not file_path:
            return
            
        self.lbl_status.setText(f"Processing: {os.path.basename(file_path)}... (This may take a minute)")
        self.lbl_status.setStyleSheet("color: blue; font-weight: bold;")
        self.btn_upload.setEnabled(False)
        QApplication.processEvents()
        
        # Generate token
        token = jwt.encode({"sub": "test_user"}, JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            with open(file_path, "rb") as f:
                files = {"files": (os.path.basename(file_path), f, "application/pdf" if file_path.endswith(".pdf") else "image/png")}
                
                # Using the URL from the input box
                url = self.url_input.text().strip()
                response = requests.post(url, headers=headers, files=files)
                
            if response.status_code == 200:
                data = response.json()
                body = data.get("body", "")
                if isinstance(body, list):
                    self.pages_html = []
                    for item in body:
                        html_val = item.get("html") if isinstance(item, dict) else item
                        
                        # Handle the case where the backend wraps a dictionary inside the list item
                        if isinstance(html_val, dict):
                            try:
                                sorted_keys = sorted(html_val.keys(), key=lambda x: int(x))
                            except (ValueError, TypeError):
                                sorted_keys = sorted(html_val.keys(), key=lambda x: str(x))
                                
                            for k in sorted_keys:
                                val = html_val[k]
                                if isinstance(val, dict) and "html" in val:
                                    self.pages_html.append(val["html"])
                                else:
                                    self.pages_html.append(str(val))
                        else:
                            self.pages_html.append(str(html_val))
                elif isinstance(body, dict):
                    # Fallback for direct dictionary format
                    try:
                        sorted_keys = sorted(body.keys(), key=lambda x: int(x))
                    except (ValueError, TypeError):
                        sorted_keys = sorted(body.keys(), key=lambda x: str(x))
                        
                    self.pages_html = []
                    for k in sorted_keys:
                        val = body[k]
                        if isinstance(val, dict) and "html" in val:
                            self.pages_html.append(val["html"])
                        else:
                            self.pages_html.append(str(val))
                else:
                    self.pages_html = [body]
                    
                self.current_page_index = 0
                self.update_view()
                self.lbl_status.setText("Done!")
                self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
            else:
                QMessageBox.critical(self, "Error", f"Server returned {response.status_code}:\n{response.text}")
                self.lbl_status.setText("Error!")
                self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.lbl_status.setText("Connection Error")
            self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
            
        self.btn_upload.setEnabled(True)

    def update_view(self):
        if not self.pages_html:
            self.web_view.setHtml("")
            return
            
        html = self.pages_html[self.current_page_index]
        self.web_view.setHtml(html)
        
        total_pages = len(self.pages_html)
        self.lbl_page_info.setText(f"Page {self.current_page_index + 1} of {total_pages}")
        
        self.btn_prev.setEnabled(self.current_page_index > 0)
        self.btn_next.setEnabled(self.current_page_index < total_pages - 1)
        
    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.update_view()
            
    def next_page(self):
        if self.current_page_index < len(self.pages_html) - 1:
            self.current_page_index += 1
            self.update_view()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = OCRViewer()
    viewer.show()
    sys.exit(app.exec())
