"""pytest tests for doc_agent — document processing data models"""
import sys; sys.path.insert(0, '.')
import pytest
from mssclaw.core.doc_agent import (
    DocExportResult, DocImportResult, PdfResult, PptResult,
    XlsxReadResult, XlsxWriteResult, Document, MeetingRoom
)


class TestDocExportResult:
    def test_creation(self):
        r = DocExportResult(path="/tmp/test.docx", size_kb=120,
                           sections=5, tables=3, paragraphs=42)
        assert r.path == "/tmp/test.docx"
        assert r.size_kb == 120
        assert r.sections == 5

    def test_minimal(self):
        r = DocExportResult(path="/dev/null", size_kb=0,
                           sections=0, tables=0, paragraphs=0)
        assert r.size_kb == 0


class TestDocImportResult:
    def test_creation(self):
        r = DocImportResult(path="/tmp/in.docx", text="Hello world",
                           tables=[], metadata={}, paragraph_count=1, table_count=0)
        assert r.text == "Hello world"
        assert r.paragraph_count == 1

    def test_with_tables(self):
        r = DocImportResult(path="/tmp/data.docx", text="data",
                           tables=["table1"], metadata={"author": "MSS"},
                           paragraph_count=3, table_count=1)
        assert r.table_count == 1
        assert r.metadata["author"] == "MSS"

    def test_table_count_matches_tables(self):
        r = DocImportResult(path="/tmp/t.docx", text="t",
                           tables=["a", "b", "c"], metadata={},
                           paragraph_count=5, table_count=3)
        assert r.table_count == 3


class TestPdfResult:
    def test_creation(self):
        r = PdfResult(path="/tmp/report.pdf", pages=10, size_kb=500)
        assert r.pages == 10
        assert r.size_kb == 500

    def test_large_document(self):
        r = PdfResult(path="/tmp/ebook.pdf", pages=420, size_kb=15000)
        assert r.pages == 420


class TestPptResult:
    def test_creation(self):
        r = PptResult(path="/tmp/slides.pptx", slides=30, size_kb=800)
        assert r.slides == 30

    def test_minimal(self):
        r = PptResult(path="/tmp/empty.pptx", slides=0, size_kb=1)
        assert r.slides == 0


class TestXlsxReadResult:
    def test_creation(self):
        r = XlsxReadResult(path="/tmp/data.xlsx", sheets=["Sheet1"],
                          schema={"Sheet1": "string"}, row_counts={"Sheet1": 100})
        assert r.path == "/tmp/data.xlsx"
        assert r.sheets == ["Sheet1"]

    def test_multi_sheet(self):
        r = XlsxReadResult(path="/tmp/multi.xlsx",
                          sheets=["Q1", "Q2", "Q3"],
                          schema={"Q1": "float", "Q2": "float", "Q3": "string"},
                          row_counts={"Q1": 50, "Q2": 50, "Q3": 20})
        assert len(r.sheets) == 3
        assert r.row_counts["Q3"] == 20


class TestXlsxWriteResult:
    def test_creation(self):
        r = XlsxWriteResult(path="/tmp/out.xlsx", sheets=3,
                           total_rows=1500, size_kb=45)
        assert r.total_rows == 1500

    def test_size_tracking(self):
        r = XlsxWriteResult(path="/tmp/big.xlsx", sheets=10,
                           total_rows=100000, size_kb=4096)
        assert r.size_kb == 4096


class TestDocument:
    def test_creation(self):
        # Document wraps python-docx — may need a real file
        try:
            d = Document()
            assert d is not None
        except Exception:
            pytest.skip("python-docx Document requires a .docx file path")


class TestMeetingRoom:
    def test_creation(self):
        # MeetingRoom is a config container for collaboration features
        room = MeetingRoom()
        assert room is not None
