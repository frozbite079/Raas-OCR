import os
import sys
import threading
from typing import Any

import requests
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick


class OcrDemoController(QObject):
    selectedFileChanged = Signal()
    apiBaseUrlChanged = Signal()
    busyChanged = Signal()
    errorMessageChanged = Signal()
    statusMessageChanged = Signal()
    pageImageSourceChanged = Signal()
    pageTitleChanged = Signal()
    pageCategoryChanged = Signal()
    fieldsModelChanged = Signal()
    filledHtmlChanged = Signal()
    currentPageChanged = Signal()
    totalPagesChanged = Signal()

    processSucceeded = Signal(object, str, str)
    processFailed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._selected_file = ""
        self._api_base_url = "http://127.0.0.1:8000"
        self._busy = False
        self._error_message = ""
        self._status_message = "Choose a PDF, then click Process."

        self._pages: list[dict[str, Any]] = []
        self._current_index = 0
        self._document_html = ""

        self._page_image_source = ""
        self._page_title = ""
        self._page_category = ""
        self._fields_model: list[dict[str, str]] = []
        self._filled_html = ""

        self.processSucceeded.connect(self._handle_process_success)
        self.processFailed.connect(self._handle_process_failure)

    @Property(str, notify=selectedFileChanged)
    def selectedFile(self) -> str:
        return self._selected_file

    @Property(str, notify=apiBaseUrlChanged)
    def apiBaseUrl(self) -> str:
        return self._api_base_url

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=pageImageSourceChanged)
    def pageImageSource(self) -> str:
        return self._page_image_source

    @Property(str, notify=pageTitleChanged)
    def pageTitle(self) -> str:
        return self._page_title

    @Property(str, notify=pageCategoryChanged)
    def pageCategory(self) -> str:
        return self._page_category

    @Property("QVariantList", notify=fieldsModelChanged)
    def fieldsModel(self) -> list[dict[str, str]]:
        return self._fields_model

    @Property(str, notify=filledHtmlChanged)
    def filledHtml(self) -> str:
        return self._filled_html

    @Property(int, notify=currentPageChanged)
    def currentPage(self) -> int:
        return self._current_index + 1 if self._pages else 0

    @Property(int, notify=totalPagesChanged)
    def totalPages(self) -> int:
        return len(self._pages)

    @Slot(str)
    def setApiBaseUrl(self, value: str) -> None:
        value = (value or "").strip().rstrip("/")
        if not value:
            return
        if value != self._api_base_url:
            self._api_base_url = value
            self.apiBaseUrlChanged.emit()

    @Slot("QVariant")
    def setSelectedFile(self, value: Any) -> None:
        path = self._coerce_local_path(value)
        if path != self._selected_file:
            self._selected_file = path
            self.selectedFileChanged.emit()

    @Slot()
    def processSelectedFile(self) -> None:
        if self._busy:
            return
        if not self._selected_file:
            self._set_error("Please choose a PDF file.")
            return
        if not os.path.exists(self._selected_file):
            self._set_error("Selected file does not exist.")
            return

        self._set_error("")
        self._set_busy(True)
        self._set_status("Processing document...")
        threading.Thread(target=self._process_worker, daemon=True).start()

    @Slot()
    def nextPage(self) -> None:
        if self._current_index < len(self._pages) - 1:
            self._current_index += 1
            self._apply_current_page()

    @Slot()
    def previousPage(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._apply_current_page()

    @Slot(object, str, str)
    def _handle_process_success(
        self, pages: list[dict[str, Any]], document_html: str, status: str
    ) -> None:
        self._pages = pages
        self._document_html = document_html or ""
        self._current_index = 0
        self.totalPagesChanged.emit()
        self._apply_current_page()
        self._set_status(status)
        self._set_busy(False)

    @Slot(str)
    def _handle_process_failure(self, message: str) -> None:
        self._set_error(message)
        self._set_status("Processing failed.")
        self._set_busy(False)

    def _process_worker(self) -> None:
        endpoint = f"{self._api_base_url}/api/ocr/extract"
        try:
            with open(self._selected_file, "rb") as file_handle:
                response = requests.post(
                    endpoint,
                    files={
                        "files": (
                            os.path.basename(self._selected_file),
                            file_handle,
                            "application/pdf",
                        )
                    },
                    data={"include_images": "true", "include_html": "true"},
                    timeout=180,
                )

            response.raise_for_status()
            payload = response.json()
            documents = payload.get("documents") or []
            if not documents:
                raise ValueError("No documents were returned by the API.")

            first_doc = documents[0]
            pages = first_doc.get("pages") or []
            if not pages:
                raise ValueError("No page data returned.")

            message = payload.get("message", "Document processed.")
            self.processSucceeded.emit(pages, first_doc.get("filled_html", ""), message)
        except Exception as exc:
            self.processFailed.emit(str(exc))

    def _apply_current_page(self) -> None:
        if not self._pages:
            self._page_image_source = ""
            self._page_title = ""
            self._page_category = ""
            self._fields_model = []
            self._filled_html = ""
        else:
            page = self._pages[self._current_index]
            image_b64 = page.get("page_image_base64", "")
            self._page_image_source = (
                f"data:image/png;base64,{image_b64}" if image_b64 else ""
            )
            self._page_title = page.get("title", "") or "Untitled"
            self._page_category = page.get("category", "") or "Unknown"

            fields = page.get("extracted_fields") or []
            normalized = []
            for field in fields:
                if isinstance(field, dict):
                    normalized.append(
                        {
                            "key": str(field.get("key", "")),
                            "value": str(field.get("value", "")),
                        }
                    )
            self._fields_model = normalized
            self._filled_html = page.get("filled_html", "") or self._document_html

        self.pageImageSourceChanged.emit()
        self.pageTitleChanged.emit()
        self.pageCategoryChanged.emit()
        self.fieldsModelChanged.emit()
        self.filledHtmlChanged.emit()
        self.currentPageChanged.emit()

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    def _set_error(self, value: str) -> None:
        if self._error_message != value:
            self._error_message = value
            self.errorMessageChanged.emit()

    def _set_status(self, value: str) -> None:
        if self._status_message != value:
            self._status_message = value
            self.statusMessageChanged.emit()

    @staticmethod
    def _coerce_local_path(value: Any) -> str:
        if isinstance(value, QUrl):
            return value.toLocalFile()
        text = str(value or "")
        if text.startswith("file://"):
            return QUrl(text).toLocalFile()
        return text


def main() -> int:
    QtWebEngineQuick.initialize()
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    controller = OcrDemoController()
    engine.rootContext().setContextProperty("controller", controller)

    qml_path = os.path.join(os.path.dirname(__file__), "Main.qml")
    engine.load(QUrl.fromLocalFile(qml_path))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
