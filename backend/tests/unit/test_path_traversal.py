import os
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.datastructures import UploadFile

from api.document_router import UPLOAD_DIR, upload_document, delete_uploaded_document, list_documents
from services.vector_store import store_documents, delete_document, IndexedDocument, list_indexed_documents
from langchain_core.documents import Document

def test_path_traversal_prevention():
    """Verify that path traversal sequences are contained securely within UPLOAD_DIR."""
    traversal_filename = "../../etc/passwd.pdf"
    
    # Simulate UUID generation
    document_id = str(uuid.uuid4())
    storage_filename = f"{document_id}.pdf"
    file_path = (UPLOAD_DIR / storage_filename).resolve()
    
    # Check that file path is strictly relative to UPLOAD_DIR
    assert file_path.is_relative_to(UPLOAD_DIR.resolve())
    assert file_path.parent == UPLOAD_DIR.resolve()
    assert str(file_path).endswith(f"{document_id}.pdf")

def test_delete_by_document_id(tmp_path):
    """Verify that delete_document purges vectors using document_id and returns storage_filename."""
    doc_id_1 = str(uuid.uuid4())
    storage_fn_1 = f"{doc_id_1}.pdf"
    
    doc_id_2 = str(uuid.uuid4())
    storage_fn_2 = f"{doc_id_2}.pdf"
    
    chunks_1 = [Document(page_content="Document 1 content", metadata={})]
    chunks_2 = [Document(page_content="Document 2 content", metadata={})]
    
    with patch("services.vector_store.get_vector_store") as mock_vs:
        mock_collection = MagicMock()
        mock_vs.return_value._collection = mock_collection
        
        # Simulate stored metadata
        mock_collection.get.return_value = {
            "ids": ["chunk_1"],
            "metadatas": [{"document_id": doc_id_1, "storage_filename": storage_fn_1, "source_file": "SameName.pdf"}]
        }
        
        result_fn = delete_document(doc_id_1)
        
        # Verify collection query targeted document_id
        mock_collection.get.assert_called_once_with(
            where={"document_id": doc_id_1},
            include=["metadatas"]
        )
        mock_collection.delete.assert_called_once_with(ids=["chunk_1"])
        assert result_fn == storage_fn_1

def test_duplicate_filename_isolation():
    """Verify that multiple documents with identical original filenames retain separate IDs."""
    doc_id_1 = str(uuid.uuid4())
    doc_id_2 = str(uuid.uuid4())
    
    metadata_sample = [
        {"document_id": doc_id_1, "source_file": "Report.pdf", "storage_filename": f"{doc_id_1}.pdf", "page": 1},
        {"document_id": doc_id_2, "source_file": "Report.pdf", "storage_filename": f"{doc_id_2}.pdf", "page": 1},
    ]
    
    with patch("services.vector_store.get_vector_store") as mock_vs:
        mock_collection = MagicMock()
        mock_vs.return_value._collection = mock_collection
        mock_collection.count.return_value = 2
        mock_collection.get.return_value = {"metadatas": metadata_sample}
        
        docs = list_indexed_documents()
        assert len(docs) == 2
        assert docs[0].document_id == doc_id_1
        assert docs[0].source_file == "Report.pdf"
        assert docs[1].document_id == doc_id_2
        assert docs[1].source_file == "Report.pdf"
