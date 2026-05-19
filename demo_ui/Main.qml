import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtWebEngine

ApplicationWindow {
    visible: true
    width: 1440
    height: 920
    title: "Raas-OCR Demo (PySide6 + QML)"

    FileDialog {
        id: filePicker
        title: "Choose a PDF file"
        nameFilters: ["PDF files (*.pdf)"]
        onAccepted: controller.setSelectedFile(selectedFile)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 62
            radius: 8
            color: "#f3f4f6"
            border.color: "#d1d5db"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Label { text: "API:" }

                TextField {
                    id: apiInput
                    Layout.preferredWidth: 340
                    text: controller.apiBaseUrl
                    onEditingFinished: controller.setApiBaseUrl(text)
                }

                Button {
                    text: "Choose PDF"
                    onClicked: filePicker.open()
                }

                Label {
                    Layout.fillWidth: true
                    text: controller.selectedFile ? controller.selectedFile : "No file selected"
                    elide: Text.ElideMiddle
                    color: "#374151"
                }

                Button {
                    text: controller.busy ? "Processing..." : "Process"
                    enabled: !controller.busy && controller.selectedFile.length > 0
                    onClicked: controller.processSelectedFile()
                }

                BusyIndicator {
                    running: controller.busy
                    visible: running
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: controller.errorMessage.length > 0 ? controller.errorMessage : controller.statusMessage
            color: controller.errorMessage.length > 0 ? "#dc2626" : "#374151"
            wrapMode: Text.Wrap
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Rectangle {
                SplitView.preferredWidth: parent.width * 0.55
                color: "#111827"
                border.color: "#374151"
                radius: 6

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    Label {
                        text: "Rendered HTML Output"
                        color: "#f9fafb"
                        font.bold: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#111111"
                        radius: 4

                        WebEngineView {
                            id: htmlView
                            anchors.fill: parent
                            anchors.margins: 4

                            onLoadingChanged: function(loadRequest) {
                                if (loadRequest.status === WebEngineView.LoadFailedStatus) {
                                    console.log("HTML render failed:", loadRequest.errorString)
                                }
                            }

                            Component.onCompleted: {
                                if (controller.filledHtml.length > 0) {
                                    loadHtml(controller.filledHtml, "about:blank")
                                } else {
                                    loadHtml("<html><body style='font-family:sans-serif;color:#ddd;background:#111;'><h3>No HTML output yet</h3></body></html>", "about:blank")
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: controller.filledHtml.length === 0
                            text: "No HTML output yet"
                            color: "#9ca3af"
                        }
                    }
                }
            }

            Rectangle {
                SplitView.preferredWidth: parent.width * 0.45
                color: "#f9fafb"
                border.color: "#d1d5db"
                radius: 6

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    Label {
                        text: controller.pageTitle.length > 0 ? controller.pageTitle : "Extracted Data"
                        font.bold: true
                        wrapMode: Text.Wrap
                    }

                    Label {
                        text: "Category: " + controller.pageCategory
                        color: "#4b5563"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 4
                        border.color: "#e5e7eb"
                        color: "white"

                        ListView {
                            anchors.fill: parent
                            anchors.margins: 6
                            clip: true
                            model: controller.fieldsModel
                            spacing: 4

                            delegate: Rectangle {
                                width: ListView.view.width
                                height: keyText.implicitHeight + valueText.implicitHeight + 12
                                color: index % 2 === 0 ? "#f9fafb" : "#ffffff"

                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 6
                                    spacing: 2

                                    Text {
                                        id: keyText
                                        text: modelData.key
                                        font.bold: true
                                        color: "#111827"
                                        wrapMode: Text.Wrap
                                    }

                                    Text {
                                        id: valueText
                                        text: modelData.value
                                        color: "#374151"
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }

                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 8

            Button {
                text: "Previous"
                enabled: controller.currentPage > 1
                onClicked: controller.previousPage()
            }

            Label {
                text: controller.totalPages > 0
                      ? ("Page " + controller.currentPage + " / " + controller.totalPages)
                      : "Page 0 / 0"
            }

            Button {
                text: "Next"
                enabled: controller.currentPage < controller.totalPages
                onClicked: controller.nextPage()
            }
        }
    }

    Connections {
        target: controller
        function onFilledHtmlChanged() {
            if (controller.filledHtml.length > 0) {
                htmlView.loadHtml(controller.filledHtml, "about:blank")
            } else {
                htmlView.loadHtml("<html><body style='font-family:sans-serif;color:#ddd;background:#111;'><h3>No HTML output yet</h3></body></html>", "about:blank")
            }
        }
    }
}
