"""Web crawler page - replaces ui_crawler.render_crawler_panel()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QSpinBox, QCheckBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from app_state import AppState
from widgets.markdown_viewer import MarkdownViewer
from widgets.status_box import StatusBox


class CrawlWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, urls, depth, max_pages, xpath, clean_mode, parent=None):
        super().__init__(parent)
        self.urls = urls
        self.depth = depth
        self.max_pages = max_pages
        self.xpath = xpath
        self.clean_mode = clean_mode

    def run(self):
        try:
            import requests
            from bs4 import BeautifulSoup
            results = []
            for url in self.urls:
                url = url.strip()
                if not url:
                    continue
                try:
                    resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                    resp.encoding = resp.apparent_encoding
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                        tag.decompose()
                    text = soup.get_text(separator='\n', strip=True)
                    title = soup.title.string if soup.title else url
                    results.append({"url": url, "title": title, "text": text[:5000]})
                except Exception as e:
                    results.append({"url": url, "title": "Error", "text": str(e)})
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class CrawlerPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("🌐 웹 크롤러")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(QLabel("URL 입력 (줄바꿈으로 구분)"))
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("https://example.com\nhttps://example2.com")
        self.url_input.setMaximumHeight(100)
        self.url_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.url_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.url_input)

        opts = QHBoxLayout()
        opts.addWidget(QLabel("Depth:"))
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 5)
        self.depth_spin.setValue(1)
        opts.addWidget(self.depth_spin)

        opts.addWidget(QLabel("Max pages:"))
        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, 50)
        self.max_spin.setValue(5)
        opts.addWidget(self.max_spin)

        self.clean_check = QCheckBox("정리 모드")
        self.clean_check.setChecked(True)
        opts.addWidget(self.clean_check)
        opts.addStretch()
        layout.addLayout(opts)

        self.btn_crawl = QPushButton("🕷️ 크롤링 시작")
        self.btn_crawl.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_crawl.clicked.connect(self._on_crawl)
        layout.addWidget(self.btn_crawl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["URL", "제목", "미리보기"])
        self.result_table.setMinimumHeight(300)
        layout.addWidget(self.result_table)

        btn_row = QHBoxLayout()
        btn_csv = QPushButton("📥 CSV 저장")
        btn_csv.clicked.connect(self._save_csv)
        btn_row.addWidget(btn_csv)
        btn_txt = QPushButton("📄 TXT 저장")
        btn_txt.clicked.connect(self._save_txt)
        btn_row.addWidget(btn_txt)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_crawl(self):
        urls = self.url_input.toPlainText().strip().split('\n')
        if not urls or not urls[0]:
            QMessageBox.warning(self, "경고", "URL을 입력하세요.")
            return

        self.btn_crawl.setEnabled(False)
        self.progress.setVisible(True)

        self._worker = CrawlWorker(urls, self.depth_spin.value(), self.max_spin.value(),
                                    "", self.clean_check.isChecked())
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(lambda e: (
            QMessageBox.critical(self, "오류", e),
            setattr(self.btn_crawl, 'enabled', True)
        ))
        self._worker.start()

    def _on_done(self, results):
        AppState.set("crawled_data", results)
        self.result_table.setRowCount(len(results))
        for i, r in enumerate(results):
            self.result_table.setItem(i, 0, QTableWidgetItem(r["url"]))
            self.result_table.setItem(i, 1, QTableWidgetItem(r["title"]))
            self.result_table.setItem(i, 2, QTableWidgetItem(r["text"][:200]))
        self.result_table.resizeColumnsToContents()
        self.progress.setVisible(False)
        self.btn_crawl.setEnabled(True)

    def _save_csv(self):
        data = AppState.get("crawled_data", [])
        if not data:
            return
        path, _ = QFileDialog.getSaveFileName(self, "CSV 저장", "crawl_result.csv", "CSV (*.csv)")
        if path:
            import csv
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=["url", "title", "text"])
                w.writeheader()
                w.writerows(data)

    def _save_txt(self):
        data = AppState.get("crawled_data", [])
        if not data:
            return
        path, _ = QFileDialog.getSaveFileName(self, "TXT 저장", "crawl_result.txt", "Text (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for r in data:
                    f.write(f"=== {r['title']} ===\n{r['url']}\n{r['text']}\n\n")

    def refresh(self):
        pass
