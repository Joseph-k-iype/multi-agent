# -*- coding: utf-8 -*-
"""
FastAPI backend for multi-agent LangGraph workflow with RAG capabilities.
Features dynamic workflow configuration, file uploads, and ChromaDB integration
with anonymized telemetry disabled.

File: backend/main.py
"""

import os
import sys
import uuid
import json
import logging
import chardet
import pandas as pd
import numpy as np
from typing import Optional, Any, Dict, List, Union, TypedDict, Annotated, Callable, Literal, Set
from pathlib import Path
import operator
import importlib
from datetime import datetime
from collections import namedtuple

# --- Core Dependencies ---
from dotenv import dotenv_values
from pydantic import BaseModel, Field, ValidationError, field_validator
import chromadb
from chromadb.config import Settings as ChromaSettings
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# --- Azure & OpenAI ---
from azure.identity import DefaultAzureCredential, get_bearer_token_provider, ClientSecretCredential
from openai import AzureOpenAI, DefaultHttpxClient

# --- LangChain & LangGraph ---
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool as lc_tool, BaseTool
from langchain_community.vectorstores import Chroma
from langchain.tools.retriever import create_retriever_tool
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain, LLMChain
from langchain.document_loaders import (
    TextLoader,
    CSVLoader, 
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Paths ---
BACKEND_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = BACKEND_DIR.parent
CONFIG_DIR = BACKEND_DIR / "config"
ENV_DIR = BACKEND_DIR / "env"
CUSTOM_TOOLS_DIR = BACKEND_DIR / "custom_tools"
UPLOADS_DIR = BACKEND_DIR / "uploads"
CHROMADB_DIR = BACKEND_DIR / "chromadb"

# Create necessary directories
for dir_path in [CONFIG_DIR, ENV_DIR, CUSTOM_TOOLS_DIR, UPLOADS_DIR, CHROMADB_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

# Default config file paths
AGENTS_CONFIG_PATH = CONFIG_DIR / "agents.json"
ORCHESTRATOR_CONFIG_PATH = CONFIG_DIR / "orchestrator.json"
TOOLS_CONFIG_PATH = CONFIG_DIR / "tools.json"
CONFIG_PATH = ENV_DIR / "config.env"
CREDS_PATH = ENV_DIR / "credentials.env"
CERT_PATH = ENV_DIR / "cacert.pem"

# Add custom tools directory to Python path
if CUSTOM_TOOLS_DIR.is_dir():
    sys.path.insert(0, str(CUSTOM_TOOLS_DIR.resolve()))
    logger.info(f"Added custom tools directory to sys.path: {CUSTOM_TOOLS_DIR.resolve()}")
else:
    logger.warning(f"Custom tools directory not found: {CUSTOM_TOOLS_DIR.resolve()}. Custom function tools may fail to load.")

# --- Utility Functions ---
Triple = namedtuple("Triple", ["subject", "predicate", "object"])

def is_file_readable(filepath: str) -> bool:
    """Check if a file is readable."""
    if not os.path.isfile(filepath) or not os.access(filepath, os.R_OK):
        raise FileNotFoundError(f"The file '{filepath}' does not exist or is not readable")
    return True

def str_to_bool(s: str) -> bool:
    """Convert a string to a boolean."""
    if isinstance(s, bool):
        return s
    if isinstance(s, str):
        if s.lower() in ('true', '1', 't', 'y', 'yes'):
            return True
        elif s.lower() in ('false', '0', 'f', 'n', 'no'):
            return False
    raise ValueError(f"Invalid boolean value: {s}")

def load_json_config(path: Path, schema: Optional[type[BaseModel]] = None) -> Union[Dict, List, None]:
    """Loads JSON config, optionally validates against a Pydantic schema."""
    if not path.is_file():
        logger.error(f"Configuration file not found: {path}")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if schema:
            # Pydantic model_validate can handle dict or list based on schema annotation
            schema.model_validate(data)
            logger.info(f"Successfully loaded and validated config: {path}")
        else:
            logger.info(f"Loaded config (no schema validation): {path}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {path}: {e}")
        return None
    except ValidationError as e:
        logger.error(f"Schema validation error for {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading config file {path}: {e}")
        return None

# --- Environment Management (Using OSEnv from sample) ---
class OSEnv:
    def __init__(self, config_file: str, creds_file: str, certificate_path: str):
        self.var_list = []
        self.bulk_set(config_file, True)
        self.bulk_set(creds_file, False)
        self.set_certificate_path(certificate_path)
        if str_to_bool(self.get("PROXY_ENABLED", "False")):
            self.set_proxy()
        
        self.credential = self._get_credential()
        
        if str_to_bool(self.get("SECURED_ENDPOINTS", "False")):
            self.token = self.get_azure_token()
        else:
            self.token = None
        
    def _get_credential(self):
        if str_to_bool(self.get("USE_MANAGED_IDENTITY", "False")):
            return DefaultAzureCredential()
        else:
            return ClientSecretCredential(
                tenant_id=self.get("AZURE_TENANT_ID"), 
                client_id=self.get("AZURE_CLIENT_ID"), 
                client_secret=self.get("AZURE_CLIENT_SECRET")
            )
    
    def set_certificate_path(self, path: str):
        try:
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            if os.path.exists(path) and is_file_readable(path):
                self.set("REQUESTS_CA_BUNDLE", path)
                self.set("SSL_CERT_FILE", path)
                self.set("CURL_CA_BUNDLE", path)
            else:
                logger.warning(f"Certificate file not found: {path}. Proceeding without certificate.")
        except Exception as e:
            logger.error(f"Error setting certificate path: {e}")
    
    def bulk_set(self, dotenvfile: str, print_val: bool = False) -> None:
        try:
            if not os.path.isabs(dotenvfile):
                dotenvfile = os.path.abspath(dotenvfile)
            if os.path.exists(dotenvfile):
                temp_dict = dotenv_values(dotenvfile)
                for key, value in temp_dict.items():
                    self.set(key, value, print_val)
                del temp_dict
            else:
                logger.warning(f"Environment file not found: {dotenvfile}. Proceeding without it.")
        except Exception as e:
            logger.error(f"Error loading environment variables from {dotenvfile}: {e}")
    
    def set(self, key: str, value: str, print_val: bool = False) -> None:
        try:
            os.environ[key] = value
            if key not in self.var_list:
                self.var_list.append(key)
            if print_val:
                logger.info(f"{key}: {value}")
        except Exception as e:
            logger.error(f"Error setting environment variable {key}: {e}")
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        try:
            return os.environ.get(key, default)
        except Exception as e:
            logger.error(f"Error getting environment variable {key}: {e}")
            return default
    
    def set_proxy(self) -> None:
        try:
            # Try with the new format first
            proxy_url = self.get("HTTPS_PROXY")
            if not proxy_url:
                # Try the format in the provided code
                ad_username = self.get("AD_USERNAME")
                ad_password = self.get("AD_USER_PW")
                proxy_domain = self.get("HTTPS_PROXY_DOMAIN")
                if all([ad_username, ad_password, proxy_domain]):
                    proxy_url = f"https://{ad_username}:{ad_password}@{proxy_domain}"
                else:
                    # Try alternative format
                    proxy_user = self.get("PROXY_USER")
                    proxy_password = self.get("PROXY_PASSWORD")
                    proxy_domain = self.get("PROXY_DOMAIN")
                    if all([proxy_user, proxy_password, proxy_domain]):
                        proxy_url = f"https://{proxy_user}:{proxy_password}@{proxy_domain}"
            
            if proxy_url:
                self.set("HTTP_PROXY", proxy_url, print_val=False)
                self.set("HTTPS_PROXY", proxy_url, print_val=False)
                
                # Set NO_PROXY for Azure domains
                no_proxy_domains = [
                    'cognitiveservices.azure.com',
                    'search.windows.net',
                    'openai.azure.com',
                    'core.windows.net',
                    'azurewebsites.net'
                ]
                self.set("NO_PROXY", ",".join(no_proxy_domains), print_val=False)
                logger.info("Proxy settings configured successfully")
            else:
                logger.warning("Proxy enabled but no proxy configuration found")
        except Exception as e:
            logger.error(f"Error setting proxy: {e}")
    
    def get_azure_token(self) -> str:
        try:
            token_provider = get_bearer_token_provider(
                self.credential,
                "https://cognitiveservices.azure.com/.default"
            )
            token = token_provider()
            self.set("AZURE_TOKEN", token, print_val=False)
            logger.info("Azure token set")
            return token
        except Exception as e:
            logger.error(f"Error retrieving Azure token: {e}")
            return None
    
    def list_env_vars(self) -> None:
        for var in self.var_list:
            if var in {'AZURE_TOKEN', 'AD_USER_PW', 'AZURE_CLIENT_SECRET', 'PROXY_PASSWORD'}:
                logger.info(f"{var}: [REDACTED]")
            else:
                logger.info(f"{var}: {os.getenv(var)}")

# --- Document and Embedding Classes ---
class MyDocument(BaseModel):
    id: str = ""
    text: str = ""
    embedding: List[float] = []
    metadata: Dict[str, Any] = {}

class EmbeddingClient:
    def __init__(self, env: OSEnv, azure_api_version: str = None, embeddings_model: str = None):
        self.env = env
        self.azure_api_version = azure_api_version or self.env.get("AZURE_OPENAI_API_VERSION", "2023-05-15")
        self.embeddings_model = embeddings_model or self.env.get("AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large")
        self.azure_endpoint = self.env.get("AZURE_OPENAI_ENDPOINT")
        self.direct_azure_client = self._get_direct_azure_client()
        
    def _get_direct_azure_client(self):
        try:
            token_provider = get_bearer_token_provider(
                self.env.credential,
                "https://cognitiveservices.azure.com/.default"
            )
            return AzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_version=self.azure_api_version,
                azure_ad_token_provider=token_provider
            )
        except Exception as e:
            logger.error(f"Error creating Azure OpenAI client: {e}")
            # Fall back to API key if available
            api_key = self.env.get("AZURE_OPENAI_API_KEY")
            if api_key:
                logger.info("Falling back to API key authentication for Azure OpenAI")
                return AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=self.azure_endpoint,
                    api_version=self.azure_api_version
                )
            raise
    
    def generate_embeddings(self, doc: MyDocument) -> MyDocument:
        try:
            # Generate embedding for the document
            response = self.direct_azure_client.embeddings.create(
                model=self.embeddings_model,
                input=doc.text
            ).data[0].embedding
            doc.embedding = response
            return doc
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return doc
    
    def generate_embeddings_batch(self, docs: List[MyDocument]) -> List[MyDocument]:
        try:
            # Extract text from each document
            texts = [doc.text for doc in docs]
            
            # Generate embeddings in a batch
            response = self.direct_azure_client.embeddings.create(
                model=self.embeddings_model,
                input=texts
            )
            
            # Update each document with its embedding
            for i, embedding_data in enumerate(response.data):
                docs[i].embedding = embedding_data.embedding
            
            return docs
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return docs
    
    def get_langchain_embeddings(self):
        """Returns a LangChain embeddings object that uses this client."""
        from langchain_core.embeddings import Embeddings  # Import correctly at the top level
        
        class CustomEmbeddings(Embeddings):
            def __init__(self, client: EmbeddingClient):
                self.client = client
            
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                docs = [MyDocument(text=text) for text in texts]
                embedded_docs = self.client.generate_embeddings_batch(docs)
                return [doc.embedding for doc in embedded_docs]
            
            def embed_query(self, text: str) -> List[float]:
                doc = MyDocument(text=text)
                embedded_doc = self.client.generate_embeddings(doc)
                return embedded_doc.embedding
        
        return CustomEmbeddings(self)

# --- AzureLLMService (enhanced with OSEnv) ---
class AzureLLMService:
    """Provides initialized Azure OpenAI LLM and Embedding clients."""
    def __init__(self, env: OSEnv):
        self.env = env
        self.embedding_client = EmbeddingClient(self.env)
        self.llm_client = self._setup_llm_client()
        self.langchain_embeddings = self.embedding_client.get_langchain_embeddings()

        if not self.llm_client:
            raise RuntimeError("Failed to initialize Azure OpenAI LLM client.")

    def _setup_llm_client(self):
        """Initializes the AzureChatOpenAI client."""
        try:
            deployment_name = self.env.get("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
            model_name = self.env.get("AZURE_OPENAI_CHAT_MODEL_NAME", deployment_name)
            api_version = self.env.get("AZURE_OPENAI_API_VERSION", "2023-05-15")
            azure_endpoint = self.env.get("AZURE_OPENAI_ENDPOINT")
            
            # Get token provider from env credential
            token_provider = get_bearer_token_provider(
                self.env.credential,
                "https://cognitiveservices.azure.com/.default"
            )
            
            llm = AzureChatOpenAI(
                azure_deployment=deployment_name,
                model=model_name,
                openai_api_version=api_version,
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=token_provider,
                temperature=float(self.env.get("DEFAULT_LLM_TEMPERATURE", 0.7)),
                max_tokens=int(self.env.get("DEFAULT_LLM_MAX_TOKENS", 1000))
            )
            logger.info(f"AzureChatOpenAI client created for deployment '{deployment_name}'.")
            return llm

        except ImportError:
             logger.critical("Import error: Ensure `langchain-openai` is installed.")
             return None
        except Exception as e:
            logger.critical(f"Critical error setting up Azure LLM client: {e}", exc_info=True)
            # Fall back to API key if available
            try:
                api_key = self.env.get("AZURE_OPENAI_API_KEY")
                if api_key:
                    logger.info("Falling back to API key authentication for Azure Chat LLM")
                    llm = AzureChatOpenAI(
                        azure_deployment=deployment_name,
                        model=model_name,
                        openai_api_version=api_version,
                        azure_endpoint=azure_endpoint,
                        api_key=api_key,
                        temperature=float(self.env.get("DEFAULT_LLM_TEMPERATURE", 0.7)),
                        max_tokens=int(self.env.get("DEFAULT_LLM_MAX_TOKENS", 1000))
                    )
                    return llm
            except Exception as fallback_error:
                logger.critical(f"Fallback authentication also failed: {fallback_error}")
            return None

# --- File Upload and RAG Integration Classes ---
class FileManager:
    """Manages file uploads, metadata, and conversion for RAG processing."""
    
    def __init__(self, upload_dir: Path, chroma_client: Optional[chromadb.Client] = None):
        self.upload_dir = upload_dir
        self.metadata_file = upload_dir / "metadata.json"
        self.file_metadata = self._load_metadata()
        self.chroma_client = chroma_client
        
    def _load_metadata(self) -> Dict:
        """Load file metadata from JSON file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading file metadata: {e}")
                return {"files": {}}
        return {"files": {}}
    
    def _save_metadata(self):
        """Save file metadata to JSON file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.file_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving file metadata: {e}")
    
    async def upload_file(self, file: UploadFile, collection_name: str = "default") -> Dict:
        """Upload a file and save metadata."""
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix.lower()
        
        # Create a unique filename
        unique_filename = f"{file_id}{file_ext}"
        file_path = self.upload_dir / unique_filename
        
        # Save the file
        try:
            with open(file_path, 'wb') as f:
                content = await file.read()
                f.write(content)
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
        
        # Store metadata
        metadata = {
            "id": file_id,
            "original_name": file.filename,
            "filename": unique_filename,
            "path": str(file_path),
            "size": os.path.getsize(file_path),
            "mime_type": file.content_type,
            "extension": file_ext,
            "upload_date": datetime.now().isoformat(),
            "collection": collection_name,
            "indexed": False
        }
        
        self.file_metadata["files"][file_id] = metadata
        self._save_metadata()
        
        return metadata
    
    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get metadata for a specific file."""
        return self.file_metadata["files"].get(file_id)
    
    def list_files(self) -> List[Dict]:
        """List all uploaded files."""
        return list(self.file_metadata["files"].values())
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file and its metadata."""
        file_info = self.get_file_info(file_id)
        if not file_info:
            return False
        
        file_path = Path(file_info["path"])
        try:
            # Remove from disk
            if file_path.exists():
                file_path.unlink()
            
            # Remove from metadata
            del self.file_metadata["files"][file_id]
            self._save_metadata()
            
            # If the file was indexed, remove it from the collection
            if file_info.get("indexed", False):
                collection_name = file_info.get("collection", "default")
                # This is a simplified approach - real implementation should be more robust
                # to handle specific document IDs
                logger.info(f"File {file_id} was indexed. Consider rebuilding collection {collection_name}.")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
    def get_loader_for_file(self, file_path: str) -> Optional[Callable]:
        """Get the appropriate document loader for a file based on its extension."""
        ext = Path(file_path).suffix.lower()
        
        loaders = {
            '.txt': TextLoader,
            '.csv': CSVLoader,
            '.pdf': PyPDFLoader,
            '.docx': Docx2txtLoader,
            '.doc': Docx2txtLoader,  # May require additional dependencies
            '.xlsx': UnstructuredExcelLoader,
            '.xls': UnstructuredExcelLoader,
        }
        
        return loaders.get(ext)
    
    def is_file_supported(self, file_path: str) -> bool:
        """Check if a file type is supported for document loading."""
        return self.get_loader_for_file(file_path) is not None

class RAGManager:
    """Manages RAG functionality with ChromaDB integration."""
    
    def __init__(self, 
                 chroma_dir: Path, 
                 embedding_client: EmbeddingClient, 
                 file_manager: FileManager):
        self.chroma_dir = chroma_dir
        self.embedding_client = embedding_client
        self.file_manager = file_manager
        self.collections = set()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        
        # Initialize ChromaDB client with anonymized telemetry disabled
        self.chroma_client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=ChromaSettings(
                anonymized_telemetry=False
            )
        )
        
        # Update file manager with chroma client
        if file_manager.chroma_client is None:
            file_manager.chroma_client = self.chroma_client
            
        # Load existing collections
        self._load_collections()
    
    def _load_collections(self):
        """Load existing collections from ChromaDB."""
        try:
            collections = self.chroma_client.list_collections()
            self.collections = {collection.name for collection in collections}
            logger.info(f"Loaded {len(self.collections)} collections: {self.collections}")
        except Exception as e:
            logger.error(f"Error loading ChromaDB collections: {e}")
            self.collections = set()
    
    def get_or_create_collection(self, collection_name: str = "default") -> chromadb.Collection:
        """Get an existing collection or create a new one."""
        try:
            if collection_name not in self.collections:
                # Create embedding function for ChromaDB
                embedding_function = self.embedding_client.get_langchain_embeddings()
                
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    embedding_function=embedding_function
                )
                self.collections.add(collection_name)
                logger.info(f"Created new collection: {collection_name}")
            else:
                collection = self.chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_client.get_langchain_embeddings()
                )
                logger.info(f"Using existing collection: {collection_name}")
            
            return collection
        except Exception as e:
            logger.error(f"Error getting/creating collection {collection_name}: {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """List all available collections."""
        return list(self.collections)
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """Get information about a collection."""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} does not exist")
        
        collection = self.chroma_client.get_collection(collection_name)
        
        # Get collection stats
        count = collection.count()
        
        return {
            "name": collection_name,
            "document_count": count,
        }
    
    def get_langchain_retriever(self, collection_name: str, search_k: int = 3):
        """Get a LangChain retriever for a collection."""
        # Create Langchain Chroma wrapper for the collection
        langchain_chroma = Chroma(
            client=self.chroma_client,
            collection_name=collection_name,
            embedding_function=self.embedding_client.get_langchain_embeddings()
        )
        
        # Create retriever
        retriever = langchain_chroma.as_retriever(
            search_kwargs={"k": search_k}
        )
        
        return retriever
    
    def get_retriever_tool(self, collection_name: str, search_k: int = 3, 
                          tool_name: Optional[str] = None, 
                          description: Optional[str] = None) -> BaseTool:
        """Create a LangChain retriever tool for a collection."""
        retriever = self.get_langchain_retriever(collection_name, search_k)
        
        tool_name = tool_name or f"{collection_name}_retriever"
        description = description or f"Searches and returns documents from the {collection_name} knowledge base."
        
        return create_retriever_tool(
            retriever,
            name=tool_name,
            description=description
        )
    
    async def add_file_to_collection(self, file_id: str, collection_name: str = "default") -> Dict:
        """Process a file and add its content to a collection."""
        file_info = self.file_manager.get_file_info(file_id)
        if not file_info:
            raise ValueError(f"File {file_id} not found")
        
        file_path = file_info["path"]
        if not self.file_manager.is_file_supported(file_path):
            raise ValueError(f"File type {file_info['extension']} is not supported for RAG indexing")
        
        # Get the appropriate loader
        loader_cls = self.file_manager.get_loader_for_file(file_path)
        loader = loader_cls(file_path)
        
        try:
            # Load and split documents
            documents = loader.load()
            splits = self.text_splitter.split_documents(documents)
            
            # Create unique document IDs based on file ID and chunk index
            doc_ids = [f"{file_id}_chunk_{i}" for i in range(len(splits))]
            
            # Convert to MyDocument format
            my_docs = []
            for i, doc in enumerate(splits):
                my_doc = MyDocument(
                    id=doc_ids[i],
                    text=doc.page_content,
                    metadata={
                        "source": file_info["original_name"],
                        "file_id": file_id,
                        "chunk_size": len(doc.page_content),
                        # Add page number if available
                        **({"page": doc.metadata["page"]} if "page" in doc.metadata else {})
                    }
                )
                my_docs.append(my_doc)
            
            # Generate embeddings
            embedded_docs = self.embedding_client.generate_embeddings_batch(my_docs)
            
            # Create embeddings and add to collection
            collection = self.get_or_create_collection(collection_name)
            
            # Prepare data for ChromaDB
            ids = [doc.id for doc in embedded_docs]
            texts = [doc.text for doc in embedded_docs]
            embeddings = [doc.embedding for doc in embedded_docs]
            metadatas = [doc.metadata for doc in embedded_docs]
            
            # Add to the collection
            collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            # Update file metadata
            file_info["indexed"] = True
            file_info["collection"] = collection_name
            file_info["chunk_count"] = len(splits)
            file_info["indexed_date"] = datetime.now().isoformat()
            
            self.file_manager.file_metadata["files"][file_id] = file_info
            self.file_manager._save_metadata()
            
            return {
                "file_id": file_id,
                "collection": collection_name,
                "chunks_added": len(splits),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error adding file {file_id} to collection {collection_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Error indexing file: {str(e)}")

# --- Tool Registry ---
class ToolRegistry:
    """Loads tool configurations and provides access to initialized tools."""
    def __init__(self, config_path: Path, llm_service: AzureLLMService, env: OSEnv, rag_manager: Optional[RAGManager] = None):
        self.env = env
        self.llm_service = llm_service
        self.rag_manager = rag_manager
        self.tools_config = load_json_config(config_path) # Load default tools config
        self.initialized_tools: Dict[str, BaseTool] = {} # Store LangChain BaseTool instances
        self.tool_definitions: Dict[str, Dict] = {} # Store raw tool config

        if not self.tools_config:
            logger.warning(f"Default tools configuration not loaded from {config_path}. Only explicitly defined custom tools might work.")
            self.tools_config = {} # Ensure it's a dict even if loading fails

        self._initialize_tools()

    def _initialize_tools(self):
        """Initializes tools based on the loaded configuration."""
        for tool_id, config in self.tools_config.items():
            if not config.get("enabled", False):
                logger.info(f"Default tool '{tool_id}' is disabled in config. Skipping initialization.")
                continue

            tool_type = config.get("type")
            tool_config = config.get("config", {})
            self.tool_definitions[tool_id] = config # Store raw config

            try:
                tool_instance: Optional[BaseTool] = None # Expect BaseTool compatible instances
                if tool_type == "chromadb":
                    # Initialize ChromaDB vectorstore if RAG manager is available
                    if self.rag_manager:
                        collection_name = tool_config.get("collection_name", "default")
                        search_k = tool_config.get("search_k", 3)
                        
                        # Create a retriever tool from the vector store
                        tool_instance = self.rag_manager.get_retriever_tool(
                            collection_name=collection_name,
                            search_k=search_k,
                            tool_name=config.get("name", f"{tool_id}_retriever"),
                            description=config.get("description", f"Searches and returns documents from the {collection_name} knowledge base.")
                        )
                    else:
                        logger.warning(f"Cannot initialize ChromaDB tool '{tool_id}': RAG manager is not available.")
                        continue
                elif tool_type == "custom_function":
                    tool_instance = self._init_custom_function(tool_id, tool_config)
                # Add more RAG-focused or internal tool types here if needed
                else:
                    logger.warning(f"Unsupported tool type '{tool_type}' for tool ID '{tool_id}'.")
                    continue

                if tool_instance:
                    # Ensure it's a LangChain BaseTool
                    if isinstance(tool_instance, BaseTool):
                         # Use the tool_id from the config as the key
                         self.initialized_tools[tool_id] = tool_instance
                         logger.info(f"Successfully initialized default tool: ID='{tool_id}' ({tool_type}) Name='{tool_instance.name}'")
                    else:
                         logger.warning(f"Initialized object for tool '{tool_id}' is not a LangChain BaseTool. Type: {type(tool_instance)}. Skipping.")

            except Exception as e:
                logger.error(f"Failed to initialize default tool '{tool_id}': {e}", exc_info=True)

    def _init_custom_function(self, tool_id: str, config: Dict) -> Optional[BaseTool]:
         """Initializes a tool based on a custom Python function."""
         module_path = config.get("module") # e.g., "formatters" (assuming it's in CUSTOM_TOOLS_DIR)
         func_name = config.get("function") # e.g., "format_as_markdown"
         # Use name from config for the tool, default to tool_id
         tool_name = config.get("name", tool_id)
         tool_description = config.get("description", f"Custom tool {tool_name}")

         if not module_path or not func_name:
              logger.error(f"Custom function tool '{tool_id}' requires 'module' and 'function' in config.")
              return None
         try:
              # Dynamically import the module (already added to sys.path)
              module = importlib.import_module(module_path)
              func = getattr(module, func_name)

              # Check if the function is already decorated with @lc_tool or is a BaseTool
              if isinstance(func, BaseTool):
                   logger.info(f"Loaded custom BaseTool '{tool_id}' from {module_path}.{func_name}")
                   # Ensure the name matches the tool_id from config if possible
                   if func.name != tool_name:
                        logger.warning(f"Custom tool ID '{tool_id}' config name '{tool_name}' mismatches tool's internal name '{func.name}'. Using '{func.name}'.")
                   return func # Already a LangChain tool

              elif hasattr(func, "langchain_tool_decorator"):
                   # If decorated with @lc_tool, it should be usable directly or provide access
                   logger.info(f"Loaded custom function tool '{tool_id}' (decorated) from {module_path}.{func_name}")
                   # Wrap it explicitly to ensure name and description from config are used
                   return Tool.from_function(func=func, name=tool_name, description=tool_description)

              else:
                   # Function is not decorated, wrap it manually
                   logger.info(f"Wrapping non-decorated function '{module_path}.{func_name}' as tool '{tool_name}'")
                   # Infer args if possible, or define them in config
                   # args_schema = ... # Define Pydantic model for args if needed
                   return Tool.from_function(
                       func=func,
                       name=tool_name,
                       description=tool_description,
                       # args_schema=args_schema # Add if needed
                   )

         except ModuleNotFoundError:
              logger.error(f"Module '{module_path}' for custom tool '{tool_id}' not found. Is it in '{CUSTOM_TOOLS_DIR}' and does it have an '__init__.py' if it's a package?")
              return None
         except AttributeError:
              logger.error(f"Function '{func_name}' not found in module '{module_path}' for custom tool '{tool_id}'.")
              return None
         except Exception as e:
              logger.error(f"Error loading custom function tool '{tool_id}': {e}", exc_info=True)
              return None


    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        """Gets an initialized tool by its ID (case-sensitive)."""
        tool = self.initialized_tools.get(tool_id)
        if not tool:
             logger.warning(f"Attempted to access tool ID '{tool_id}' but it was not found in initialized default tools.")
        return tool

    def get_tools_for_agent(self, agent_config: Dict) -> List[BaseTool]:
         """Gets the list of initialized BaseTool instances allowed for a specific agent config."""
         allowed_tool_ids = agent_config.get("allowed_tools", [])
         agent_tools = []
         if not isinstance(allowed_tool_ids, list):
              logger.warning(f"Agent '{agent_config.get('id')}': 'allowed_tools' is not a list, skipping tool loading.")
              return []
         for tool_id in allowed_tool_ids:
              if not isinstance(tool_id, str):
                   logger.warning(f"Agent '{agent_config.get('id')}': Invalid tool ID type in allowed_tools: {type(tool_id)}. Skipping.")
                   continue
              tool = self.get_tool(tool_id) # Use the ID from agents.json
              if tool:
                   # Ensure the tool name used by the LLM matches the ID if possible
                   if tool.name != tool_id:
                        logger.warning(f"Tool ID '{tool_id}' in agent config differs from actual tool name '{tool.name}'. LLM will use '{tool.name}'.")
                   agent_tools.append(tool)
              else:
                   # Log the ID from agents.json that failed
                   logger.warning(f"Agent '{agent_config.get('id')}' requires tool '{tool_id}', but it's unavailable in the default tool registry.")
         return agent_tools

# --- LangGraph State Definition ---
class AgentState(TypedDict):
    """Defines the structure of the state passed between agent nodes."""
    initial_task: str
    research_findings: Optional[str] # Example state field for RAG output
    draft_content: Optional[str]
    final_content: Optional[str]
    error_message: Optional[str]
    current_step: int
    messages: Annotated[List[BaseMessage], operator.add]

# --- Agent Executor Node ---
class AgentNode:
    """Represents a node in the LangGraph graph that executes an agent's logic."""
    def __init__(self, agent_config: Dict, llm_service: AzureLLMService, tool_registry: ToolRegistry):
        # Validate essential agent config keys
        if not agent_config.get("id"): raise ValueError("Agent config missing 'id'")
        self.agent_id = agent_config["id"]
        self.config = agent_config
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.role = agent_config.get("role", "Agent")
        self.goal = agent_config.get("goal", "Process information")
        self.initial_state = agent_config.get("initial_state", {})

        # Get LLM instance, potentially configure it based on agent spec
        self.llm = self._configure_llm(llm_service.llm_client, agent_config.get("llm_config"))

        # Get tools allowed for this agent
        self.tools = tool_registry.get_tools_for_agent(agent_config)
        logger.info(f"AgentNode '{self.agent_id}' initialized with {len(self.tools)} tools: {[t.name for t in self.tools]}")

        # Bind tools to the LLM if the LLM supports tool calling
        if self.tools and hasattr(self.llm, "bind_tools"):
             logger.info(f"Binding {len(self.tools)} tools to LLM for agent '{self.agent_id}'")
             try:
                  self.llm_with_tools = self.llm.bind_tools(self.tools)
             except Exception as e:
                  logger.error(f"Failed to bind tools for agent '{self.agent_id}': {e}. Proceeding without bound tools.")
                  self.llm_with_tools = self.llm
        else:
             self.llm_with_tools = self.llm # Use base LLM if no tools or binding not supported


    def _configure_llm(self, base_llm: AzureChatOpenAI, agent_llm_config: Optional[Dict]):
        """Creates a potentially agent-specific LLM configuration using bind."""
        if not agent_llm_config or not isinstance(agent_llm_config, dict):
            return base_llm # Use the shared service LLM

        # Parameters that can typically be overridden via bind
        valid_params = ["temperature", "max_tokens", "top_p", "stop"] # Add others if needed
        config_params = {k: agent_llm_config[k] for k in valid_params if k in agent_llm_config}

        if config_params:
             logger.info(f"Agent '{self.agent_id}' overriding LLM params: {config_params}")
             try:
                # Use .bind() to create a runnable with new parameters without modifying the original
                return base_llm.bind(**config_params)
             except Exception as e:
                  logger.error(f"Failed to bind LLM parameters for agent '{self.agent_id}': {e}. Using base LLM.")
                  return base_llm
        else:
             return base_llm


    def _construct_prompt_text(self, task: str, state: AgentState) -> str:
         """Constructs the core task prompt text for the agent."""
         prompt_text = f"You are an AI Agent playing the role of: {self.role}.\n"
         prompt_text += f"Your primary goal is: {self.goal}\n\n"

         agent_knowledge = {**self.initial_state}
         if agent_knowledge:
              prompt_text += f"Your static knowledge/configuration:\n{json.dumps(agent_knowledge, indent=2)}\n\n"

         # Selectively include relevant parts of the dynamic workflow state
         # Exclude sensitive or overly verbose fields if necessary
         relevant_state = {k: v for k, v in state.items() if k not in ['messages', 'current_step', 'initial_task'] and v is not None}
         if relevant_state:
              prompt_text += f"Current workflow context:\n{json.dumps(relevant_state, indent=2)}\n\n"

         prompt_text += f"Your current task is:\n'''\n{task}\n'''\n\n"
         prompt_text += "Perform this task based on your role, goal, knowledge, the provided context, and message history. Use available tools ONLY if necessary to achieve your goal (e.g., use the retriever tool to find relevant information before answering). Respond clearly with your result for the task." # Added RAG hint
         return prompt_text

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """The method executed by LangGraph when this node is invoked."""
        logger.info(f"--- Executing Agent Node: {self.agent_id} ---")
        # Create a dictionary for updates to the state for this step
        updates: Dict[str, Any] = {"current_step": state.get('current_step', 0) + 1}
        logger.debug(f"Received state (step {updates['current_step']}): {state}")

        # Determine the task for this agent based on the workflow state
        task = self._determine_task(state)
        if not task:
             logger.error(f"Agent '{self.agent_id}' could not determine task from state.")
             updates["error_message"] = f"Task determination failed for {self.agent_id}"
             # Append error message to history (return only the new message)
             updates["messages"] = [AIMessage(content=f"Error: Task determination failed for {self.agent_id}")]
             return updates # Return immediately with error

        logger.info(f"Agent '{self.agent_id}' determined task: {task[:150]}...")

        # Construct prompt and messages for the LLM
        system_message = f"You are {self.role}. Your goal is: {self.goal}."
        human_prompt = self._construct_prompt_text(task, state)

        # Prepare message history for the LLM call
        # LangGraph state accumulates messages via operator.add
        messages_for_llm = [SystemMessage(content=system_message)] + state["messages"] + [HumanMessage(content=human_prompt)]

        # Invoke LLM (potentially with tools)
        try:
            response_message: AIMessage = self.llm_with_tools.invoke(messages_for_llm)
            logger.debug(f"LLM raw response type: {type(response_message)}")
            logger.debug(f"LLM raw response content: {response_message}")

            # Tool call handling is managed by graph routing. This node returns the AIMessage.
            # If it contains tool_calls, the conditional edge routes to the ToolNode.

        except Exception as e:
            logger.error(f"Error during LLM invocation for agent '{self.agent_id}': {e}", exc_info=True)
            updates["error_message"] = f"LLM invocation failed for {self.agent_id}: {e}"
            # Append error message to history
            updates["messages"] = [AIMessage(content=f"Error during LLM invocation: {e}")]
            return updates # Return immediately with error

        # Map the LLM's response content (if any) to the appropriate state field
        # Only map if there's actual content and no tool calls (tool results handled later)
        if response_message.content and not response_message.tool_calls:
            output_content = response_message.content if isinstance(response_message.content, str) else json.dumps(response_message.content)
            state_mapping_updates = self._map_output_to_state(output_content or "", state)
            updates.update(state_mapping_updates)
        elif response_message.tool_calls:
             logger.info(f"Agent '{self.agent_id}' generated tool calls. Content mapping skipped, routing to ToolNode.")
        else:
             logger.info(f"Agent '{self.agent_id}' response has no content and no tool calls.")


        # IMPORTANT: Return the AIMessage itself to be added to the state's message list
        # LangGraph's `operator.add` for the 'messages' field handles appending.
        updates["messages"] = [response_message] # Return only the new message to be appended

        logger.info(f"Agent '{self.agent_id}' finished invocation. Proposing state updates.")
        logger.debug(f"Proposed updates (excluding messages): { {k:v for k,v in updates.items() if k != 'messages'} }")
        return updates


    def _determine_task(self, state: AgentState) -> Optional[str]:
        """Logic to determine the current task based on agent ID and workflow state."""
        agent_id = self.agent_id
        # Example logic based on typical agent roles, adapt as needed
        if agent_id.startswith("researcher"): # More generic check
            # Researcher likely always starts with the initial task or refines based on feedback
            # Task might involve using the RAG tool (chromadb_retriever)
            return f"Find relevant information for the initial task: '{state.get('initial_task', 'No initial task provided.')}'. Use the retriever tool."
        elif agent_id.startswith("writer"):
            findings = state.get("research_findings") # This state field should contain RAG results
            if findings:
                writer_config = self.config.get("initial_state", {})
                tone = writer_config.get("tone", "neutral")
                audience = writer_config.get("audience", "general")
                format_req = writer_config.get("format", "text")
                return f"Synthesize the following retrieved information into content in '{format_req}' format, adopting a {tone} tone for a {audience} audience:\n\n{findings}"
            else:
                logger.error(f"Writer agent '{agent_id}' cannot proceed: Missing 'research_findings' (RAG results) in state.")
                return None # Indicate task cannot be determined
        elif agent_id.startswith("editor"):
            draft = state.get("draft_content")
            if draft:
                 editor_config = self.config.get("initial_state", {})
                 guidelines = editor_config.get("guidelines", "standard editing guidelines")
                 return f"Review and edit the following draft content according to these guidelines '{guidelines}':\n\n{draft}"
            else:
                logger.error(f"Editor agent '{agent_id}' cannot proceed: Missing 'draft_content' in state.")
                return None # Indicate task cannot be determined
        else:
            # Fallback for agents not explicitly handled above
            logger.warning(f"No specific task determination logic defined for agent: {agent_id}. Using initial task as fallback.")
            return state.get("initial_task")


    def _map_output_to_state(self, output: str, current_state: AgentState) -> Dict[str, Any]:
        """Maps the agent's output content to the corresponding fields in the graph state."""
        agent_id = self.agent_id
        # Example mapping logic
        if agent_id.startswith("researcher"):
            # Assuming the researcher's output *is* the findings from RAG or synthesis
            return {"research_findings": output}
        elif agent_id.startswith("writer"):
            return {"draft_content": output}
        elif agent_id.startswith("editor"):
            # Assuming editor provides the final version
            return {"final_content": output}
        else:
            # Generic fallback: store output under a key named after the agent
            logger.warning(f"No specific output mapping logic defined for agent: {agent_id}. Storing in '{agent_id}_output'.")
            return {f"{agent_id}_output": output}

# --- Workflow Graph Builder ---
class WorkflowGraph:
    """Builds and runs the LangGraph workflow based on configurations."""
    def __init__(self, agents_config: List[Dict], orchestrator_config: Dict, llm_service: AzureLLMService, tool_registry: ToolRegistry):
        # Deep copy configurations to avoid modifying originals if needed elsewhere
        self.agents_config = {cfg["id"]: cfg.copy() for cfg in agents_config}
        self.orchestrator_config = orchestrator_config.copy()
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.graph_builder = StateGraph(AgentState) # Use builder attribute
        self.compiled_graph = None # Compiled graph stored here
        self._build_graph() # Build the graph upon instantiation

    def _validate_configs(self):
        """Performs basic validation on the structure of agent/orchestrator configs."""
        if not self.orchestrator_config.get("nodes"):
            raise ValueError("Orchestrator config missing 'nodes' list.")
        if not self.orchestrator_config.get("entry_point"):
            raise ValueError("Orchestrator config missing 'entry_point'.")

        defined_node_ids = {node["id"] for node in self.orchestrator_config["nodes"]}
        agent_config_ids = set(self.agents_config.keys())

        if not defined_node_ids.issubset(agent_config_ids):
            missing_agents = defined_node_ids - agent_config_ids
            raise ValueError(f"Agent configurations missing for nodes defined in orchestrator: {missing_agents}")

        entry_point = self.orchestrator_config["entry_point"]
        if entry_point not in defined_node_ids:
            raise ValueError(f"Entry point '{entry_point}' is not defined in orchestrator nodes.")

        finish_points = self.orchestrator_config.get("finish_point", [])
        if isinstance(finish_points, str): finish_points = [finish_points]
        for fp in finish_points:
            if fp not in defined_node_ids:
                 logger.warning(f"Finish point '{fp}' is not defined in orchestrator nodes.") # Warning, not error

        if "edges" not in self.orchestrator_config:
             logger.warning("Orchestrator config has no 'edges' defined. Workflow might only run the entry point.")
             self.orchestrator_config["edges"] = [] # Ensure edges list exists

        for edge in self.orchestrator_config["edges"]:
             if edge.get("source") not in defined_node_ids:
                  raise ValueError(f"Edge source '{edge.get('source')}' is not a defined node.")
             if edge.get("target") not in defined_node_ids:
                  raise ValueError(f"Edge target '{edge.get('target')}' is not a defined node.")

        logger.info("Basic configuration validation passed.")


    def _build_graph(self):
        """Constructs the LangGraph based on orchestrator.json."""
        logger.info("Building LangGraph workflow dynamically...")
        self._validate_configs() # Perform validation first

        # 1. Add Agent Nodes
        node_configs = self.orchestrator_config.get("nodes", [])
        agent_nodes: Dict[str, AgentNode] = {} # Store instances for tool node reference
        agent_has_tools: Dict[str, bool] = {} # Track which agents use tools
        for node_cfg in node_configs:
            agent_id = node_cfg["id"]
            # Already validated that agent_config exists
            agent_config = self.agents_config[agent_id]

            try:
                agent_node_instance = AgentNode(agent_config, self.llm_service, self.tool_registry)
                agent_nodes[agent_id] = agent_node_instance # Store instance
                agent_has_tools[agent_id] = bool(agent_node_instance.tools) # Check if this agent has tools
                self.graph_builder.add_node(agent_id, agent_node_instance) # Add agent node instance
                logger.info(f"Added agent node to graph: '{agent_id}' (Has Tools: {agent_has_tools[agent_id]})")
            except Exception as e:
                 logger.error(f"Failed to initialize AgentNode for ID '{agent_id}': {e}", exc_info=True)
                 raise ValueError(f"Error initializing agent node '{agent_id}'.") from e

        # 2. Add Tool Node (if any agent uses tools)
        any_agent_uses_tools = any(agent_has_tools.values())
        all_tools = list(self.tool_registry.initialized_tools.values())
        tool_node_added = False
        if any_agent_uses_tools:
             if not all_tools:
                  logger.warning("Agents are configured to use tools, but no tools were successfully initialized in ToolRegistry. Tool calls will likely fail.")
             else:
                  logger.info(f"Adding ToolNode with tools: {[tool.name for tool in all_tools]}")
                  tool_node = ToolNode(all_tools)
                  self.graph_builder.add_node("tool_executor", tool_node)
                  tool_node_added = True
        else:
             logger.info("No agents configured with tools. ToolNode not added.")


        # 3. Set Entry Point
        entry_point = self.orchestrator_config["entry_point"] # Already validated
        self.graph_builder.set_entry_point(entry_point)
        logger.info(f"Set graph entry point: '{entry_point}'")

        # 4. Add Edges and Conditional Edges
        edges = self.orchestrator_config.get("edges", [])
        all_graph_node_ids = set(agent_nodes.keys()) | ({"tool_executor"} if tool_node_added else set())

        # Define finish points early for routing logic
        finish_points_cfg = self.orchestrator_config.get("finish_point", [])
        finish_points = [finish_points_cfg] if isinstance(finish_points_cfg, str) else finish_points_cfg


        # Iterate through agent nodes to define their outgoing edges
        for agent_id in agent_nodes.keys():
            # Find the direct target specified in orchestrator.json for this agent
            next_agent_target = self._find_direct_target(agent_id, edges, all_graph_node_ids)

            # Determine the final destination if 'continue' is chosen (next agent or END)
            target_node_for_continue = next_agent_target if next_agent_target else END

            if agent_has_tools[agent_id] and tool_node_added:
                # Agent uses tools: Add conditional edge
                logger.info(f"Adding conditional edge from agent: '{agent_id}' -> (tools? tool_executor : {target_node_for_continue})")
                self.graph_builder.add_conditional_edges(
                    agent_id,
                    self._should_continue_or_use_tool,
                    {
                        "continue": target_node_for_continue, # Route to next agent or END
                        "tools": "tool_executor" # Route to tool executor
                    }
                )
                # Add edge from ToolNode back to this agent
                self.graph_builder.add_edge("tool_executor", agent_id)
                logger.info(f"Added edge: tool_executor -> {agent_id}")
            else:
                # Agent does not use tools: Add direct edge to next agent or END
                self.graph_builder.add_edge(agent_id, target_node_for_continue)
                logger.info(f"Added direct edge: {agent_id} -> {target_node_for_continue}")


        # 5. Compile the graph
        try:
            checkpointer = SqliteSaver.from_conn_string(":memory:")
        except AttributeError:
            # Fallback for newer versions of LangGraph
            from langgraph.checkpoint import MemorySaver
            checkpointer = MemorySaver() # In-memory checkpointer for simplicity
        self.compiled_graph = self.graph_builder.compile(checkpointer=checkpointer)
        logger.info("LangGraph workflow compiled successfully.")

    def _should_continue_or_use_tool(self, state: AgentState) -> Literal["continue", "tools"]:
        """Determines routing based on whether the last message has tool calls."""
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        # Check if the last message is an AIMessage and if it has tool_calls
        if isinstance(last_message, AIMessage) and getattr(last_message, 'tool_calls', None):
            logger.debug(f"Routing decision from step {state.get('current_step', '?')}: Use tools")
            return "tools"
        logger.debug(f"Routing decision from step {state.get('current_step', '?')}: Continue")
        return "continue"

    def _find_direct_target(self, current_agent_id: str, edges: List[Dict], all_graph_node_ids: set) -> Optional[str]:
        """Finds the valid target defined in orchestrator.json edges for the current agent."""
        target = None
        for edge in edges:
            if edge.get("source") == current_agent_id:
                target = edge.get("target")
                # Target must be a node defined in the graph (agent or tool executor)
                if target in all_graph_node_ids:
                     logger.debug(f"Found direct edge target for '{current_agent_id}': '{target}'")
                     return target
                else:
                     logger.warning(f"Edge target '{target}' for source '{current_agent_id}' is not a valid node ID in the graph. Ignoring this edge.")
                     return None # Indicate no valid target found in this edge

        logger.debug(f"No valid outgoing edge defined in orchestrator config for agent '{current_agent_id}'.")
        return None # Indicate no target defined


    def run(self, initial_task: str) -> Dict[str, Any]:
        """Runs the compiled graph with the initial task. Returns final state dict."""
        if not self.compiled_graph:
            raise RuntimeError("Graph is not compiled.")

        initial_state_payload: AgentState = {
            "initial_task": initial_task,
            "research_findings": None,
            "draft_content": None,
            "final_content": None,
            "error_message": None,
            "current_step": 0,
            "messages": [] # Start with empty message history
        }

        # Define a configuration for the run, e.g., a unique thread ID
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        logger.info(f"Starting graph execution with thread_id: {thread_id}")
        final_state = None
        try:
            # Use stream or invoke. Invoke gets the final state.
            final_state = self.compiled_graph.invoke(initial_state_payload, config=config)
            logger.info("Graph execution completed.")
            logger.debug(f"Final state dictionary: {final_state}")

            # Ensure final_state is a dictionary
            if not isinstance(final_state, dict):
                 logger.error(f"Graph execution returned unexpected type: {type(final_state)}. Expected dict.")
                 # Attempt to recover state from checkpointer if possible (advanced)
                 # For now, return a basic error state
                 return {
                    "error_message": "Workflow execution returned unexpected state format.",
                    "thread_id": thread_id,
                    "initial_task": initial_task,
                    "messages": [],
                    "current_step": -1 # Indicate error state
                 }

            # Add thread_id for response consistency
            final_state["thread_id"] = thread_id
            return final_state

        except Exception as e:
             logger.error(f"Error during graph execution: {e}", exc_info=True)
             # Return an error state dictionary
             return {
                 "error_message": f"Workflow execution failed: {str(e)}",
                 "thread_id": thread_id,
                 "initial_task": initial_task, # Include initial task for context
                 "messages": [], # Empty messages on error
                 "current_step": -1 # Indicate error state
            }

# --- API Models ---
# Pydantic models for request and response validation
class AgentConfig(BaseModel):
    id: str
    name: str = "Unnamed Agent"
    role: str = "Generic Agent"
    goal: str = "Process information."
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    llm_config: Optional[Dict[str, Any]] = None
    allowed_tools: List[str] = Field(default_factory=list)

class OrchestratorEdge(BaseModel):
    source: str
    target: str

class OrchestratorNode(BaseModel):
    id: str # Must match an AgentConfig ID

class OrchestratorConfig(BaseModel):
    entry_point: str
    finish_point: Union[str, List[str]] # Allow single or list
    nodes: List[OrchestratorNode] # List of nodes with just their IDs
    edges: List[OrchestratorEdge]

class WorkflowRequest(BaseModel):
    initial_task: str = Field(..., min_length=1, examples=["Explain the concept of RAG."])
    agents_config: List[AgentConfig] # Dynamic agent definitions from UI
    orchestrator_config: OrchestratorConfig # Dynamic workflow definition from UI

class WorkflowResponse(BaseModel):
    thread_id: str
    final_state: Dict[str, Any] # The final AgentState dictionary (with messages potentially stringified)

class FileUploadResponse(BaseModel):
    file_id: str
    original_name: str
    size: int
    status: str = "success"
    mime_type: Optional[str] = None
    
class FileIndexingRequest(BaseModel):
    file_id: str
    collection: str = "default"
    
class FileIndexingResponse(BaseModel):
    file_id: str
    collection: str
    chunks_added: int
    status: str

class FileListResponse(BaseModel):
    files: List[Dict]
    count: int

class CollectionListResponse(BaseModel):
    collections: List[str]
    default_collection: str = "default"

class ChatRequest(BaseModel):
    message: str
    history: List[Dict] = []
    collection: Optional[str] = "default"
    
class ChatResponse(BaseModel):
    message_id: str
    content: str
    sources: Optional[List[Dict]] = None

# --- FastAPI App ---
app = FastAPI(title="Multi-Agent Workflow API (RAG Focused)", 
              description="API to run LangGraph multi-agent workflows defined by JSON configurations, focused on RAG.")

# Configure CORS
origins = [
    "http://localhost:3000", # Default React dev server port
    "http://localhost:5173", # Default Vite dev server port
    # Add other origins if needed (e.g., your deployed frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for uploaded content if needed
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# --- Global instances (initialized on startup) ---
# These shared components are initialized once for efficiency
env_global: Optional[OSEnv] = None
llm_service_global: Optional[AzureLLMService] = None
tool_registry_global: Optional[ToolRegistry] = None
file_manager_global: Optional[FileManager] = None
rag_manager_global: Optional[RAGManager] = None

@app.on_event("startup")
def startup_event():
    """Initialize global components needed by all requests."""
    global env_global, llm_service_global, tool_registry_global, file_manager_global, rag_manager_global
    logger.info("FastAPI application startup: Initializing shared components...")
    try:
        # Ensure config directories exist
        CONFIG_DIR.mkdir(exist_ok=True)
        ENV_DIR.mkdir(exist_ok=True)
        CUSTOM_TOOLS_DIR.mkdir(exist_ok=True)
        UPLOADS_DIR.mkdir(exist_ok=True)
        CHROMADB_DIR.mkdir(exist_ok=True)

        # Initialize environment with OSEnv (as provided in your code)
        env_global = OSEnv(str(CONFIG_PATH), str(CREDS_PATH), str(CERT_PATH))
        
        # Initialize LLM service
        llm_service_global = AzureLLMService(env=env_global)
        
        # Initialize file manager (without ChromaDB initially)
        file_manager_global = FileManager(upload_dir=UPLOADS_DIR)
        
        # Initialize RAG manager if embeddings are available
        embedding_client = llm_service_global.embedding_client
        if embedding_client:
            logger.info("Initializing RAG manager with ChromaDB...")
            rag_manager_global = RAGManager(
                chroma_dir=CHROMADB_DIR,
                embedding_client=embedding_client,
                file_manager=file_manager_global
            )
            
            # Update file manager with ChromaDB client
            file_manager_global.chroma_client = rag_manager_global.chroma_client
        else:
            logger.warning("Embedding client not available. RAG functionality disabled.")
        
        # Initialize tool registry (after RAG so it can use RAG tools)
        tool_registry_global = ToolRegistry(
            config_path=TOOLS_CONFIG_PATH,
            llm_service=llm_service_global,
            env=env_global,
            rag_manager=rag_manager_global
        )
        
        logger.info("Shared components initialized successfully.")
    except Exception as e:
        logger.critical(f"FATAL: Failed to initialize shared components on startup: {e}", exc_info=True)
        # Prevent app from starting properly if core components fail
        # FastAPI might still start but endpoints relying on these will fail
        env_global = None
        llm_service_global = None
        tool_registry_global = None
        file_manager_global = None
        rag_manager_global = None
        # Optionally raise RuntimeError to halt startup completely
        # raise RuntimeError("Failed to initialize core services during startup.") from e

# --- Dependency for checking service health ---
def get_service_dependencies() -> Dict[str, bool]:
    """Get the status of service dependencies as a dict."""
    return {
        "env": env_global is not None,
        "llm_service": llm_service_global is not None,
        "tool_registry": tool_registry_global is not None,
        "file_manager": file_manager_global is not None,
        "rag_manager": rag_manager_global is not None
    }

# --- API Endpoints ---
@app.post("/run-workflow",
          response_model=WorkflowResponse,
          summary="Run Dynamically Defined Multi-Agent Workflow",
          description="Builds and runs a LangGraph workflow based on the agent and orchestrator configurations provided in the request body.")
async def run_workflow_endpoint(
    request: WorkflowRequest = Body(...),
    dependencies: Dict[str, bool] = Depends(get_service_dependencies)
):
    """
    Builds and runs the multi-agent workflow based on dynamic configuration.
    """
    # Check if global components initialized correctly during startup
    if not dependencies["llm_service"] or not dependencies["tool_registry"]:
        logger.error("Core services (LLM, Tools) not initialized properly during startup.")
        raise HTTPException(status_code=503, detail="Core services not available. Check server logs.")

    logger.info(f"Received dynamic workflow request with task: '{request.initial_task[:50]}...'")
    logger.debug(f"Received Agents Config Count: {len(request.agents_config)}")
    logger.debug(f"Received Orchestrator Config: {request.orchestrator_config.model_dump()}")

    try:
        # FastAPI automatically validates the request body against WorkflowRequest model

        # Build the graph dynamically based on the request
        # Pass dict representations of the Pydantic models
        workflow_graph = WorkflowGraph(
            agents_config=[agent.model_dump() for agent in request.agents_config],
            orchestrator_config=request.orchestrator_config.model_dump(),
            llm_service=llm_service_global,
            tool_registry=tool_registry_global # Use the globally initialized tool registry
        )

        if not workflow_graph.compiled_graph:
             logger.error("Failed to compile the dynamic workflow graph.")
             # This might indicate an issue caught during _build_graph's validation
             raise HTTPException(status_code=500, detail="Failed to build workflow from provided configuration.")

        # Run the dynamically built graph
        final_state_dict = workflow_graph.run(initial_task=request.initial_task)

        # Extract thread_id (already added in the run method)
        thread_id = final_state_dict.pop("thread_id", "unknown") # Remove for response model

        # Convert BaseMessages to a more serializable format for JSON response
        if 'messages' in final_state_dict and isinstance(final_state_dict['messages'], list):
             serializable_messages = []
             for msg in final_state_dict['messages']:
                  msg_repr = {}
                  try:
                      # Attempt structured serialization first
                      if hasattr(msg, 'type'): msg_repr['type'] = msg.type
                      if hasattr(msg, 'content'): msg_repr['content'] = msg.content
                      if isinstance(msg, AIMessage) and getattr(msg, 'tool_calls', None):
                           # Serialize tool calls if present
                           msg_repr['tool_calls'] = msg.tool_calls
                      if isinstance(msg, ToolMessage) and getattr(msg, 'tool_call_id', None):
                           msg_repr['tool_call_id'] = msg.tool_call_id
                           # Include content which is the tool's output
                           if hasattr(msg, 'content'): msg_repr['tool_output'] = msg.content

                      # If basic fields captured, use the dict, else fallback
                      serializable_messages.append(msg_repr if 'type' in msg_repr else str(msg))
                  except Exception as serialization_error:
                       logger.warning(f"Could not serialize message object: {serialization_error}. Falling back to string.")
                       serializable_messages.append(str(msg)) # Fallback

             final_state_dict['messages'] = serializable_messages

        return WorkflowResponse(
            thread_id=thread_id,
            final_state=final_state_dict
        )
    except ValidationError as e:
         # This catches Pydantic validation errors if FastAPI didn't catch them earlier
         logger.error(f"Invalid configuration received (Pydantic validation): {e}")
         raise HTTPException(status_code=422, detail=f"Invalid configuration provided: {e}")
    except ValueError as e: # Catch specific errors during graph building or validation
         logger.error(f"Error processing configuration or building graph: {e}", exc_info=True)
         # Provide a more specific error message if possible
         raise HTTPException(status_code=400, detail=f"Error in workflow configuration: {e}")
    except Exception as e:
        # Catch-all for other unexpected errors during execution
        logger.error(f"Error running dynamic workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

# --- File Upload and RAG Endpoints ---
@app.post("/upload-files", 
        response_model=List[FileUploadResponse],
        summary="Upload files for RAG processing")
async def upload_files(
    files: List[UploadFile] = File(...), 
    collection: str = Form("default"),
    dependencies: Dict[str, bool] = Depends(get_service_dependencies)
):
    """Upload multiple files for later RAG processing."""
    if not dependencies["file_manager"]:
        raise HTTPException(status_code=503, detail="File manager service not available")
    
    responses = []
    
    for file in files:
        try:
            file_info = await file_manager_global.upload_file(file, collection)
            responses.append(FileUploadResponse(
                file_id=file_info["id"],
                original_name=file_info["original_name"],
                size=file_info["size"],
                mime_type=file_info["mime_type"]
            ))
        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    
    return responses

@app.post("/index-file", 
        response_model=FileIndexingResponse,
        summary="Index an uploaded file for RAG")
async def index_file(
    request: FileIndexingRequest,
    dependencies: Dict[str, bool] = Depends(get_service_dependencies)
):
    """Process a previously uploaded file and add to the vector database."""
    if not dependencies["rag_manager"]:
        raise HTTPException(status_code=503, detail="RAG manager service not available")
    
    try:
        result = await rag_manager_global.add_file_to_collection(
            file_id=request.file_id,
            collection_name=request.collection
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error indexing file: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

@app.get("/list-files", 
        response_model=FileListResponse,
        summary="List all uploaded files")
def list_files(
    dependencies: Dict[str, bool] = Depends(get_service_dependencies)
):
    """List all files that have been uploaded."""
    if not dependencies["file_manager"]:
        raise HTTPException(status_code=503, detail="File manager service not available")
    
    files = file_manager_global.list_files()
    return {
        "files": files,
        "count": len(files)
    }

@app.get("/list-collections", 
        response_model=CollectionListResponse,
        summary="List all available collections")
def list_collections(
    dependencies: Dict[str, bool] = Depends(get_service_dependencies)
):
    """List all available collections in the vector database."""
    if not dependencies["rag_manager"]:
        raise HTTPException(status_code=503, detail="RAG manager service not available")
    
    collections = rag_manager_global.list_collections()
    return {
        "collections": collections,
        "default_collection": "default"
    }

@app.get("/collection-info/{collection_name}",
        summary="Get information about a collection")
def get_collection_info(
    collection_name: str,
    dependencies: Dict[str, bool] = Depends(get_service_dependencies)
):
    """Get information about a specific collection."""
    if not dependencies["rag_manager"]:
        raise HTTPException(status_code=503, detail="RAG manager service not available")
    
    try:
        return rag_manager_global.get_collection_info(collection_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving collection info: {str(e)}")

@app.delete("/delete-file/{file_id}",
        summary="Delete an uploaded file")
def delete_file(
    file_id: str,
    dependencies: Dict[str, bool] = Depends(get_service_dependencies)
):
    """Delete an uploaded file and its metadata."""
    if not dependencies["file_manager"]:
        raise HTTPException(status_code=503, detail="File manager service not available")
    
    success = file_manager_global.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found or could not be deleted")
    return {"status": "success", "file_id": file_id}

@app.post("/chat",
        response_model=ChatResponse,
        summary="Chat with RAG-enabled agents")
async def chat(
    request: ChatRequest,
    dependencies: Dict[str, bool] = Depends(get_service_dependencies)
):
    """Chat endpoint for interacting with RAG-enabled agents."""
    # Check if services are available
    missing_services = [k for k, v in dependencies.items() if not v and k in ["llm_service", "rag_manager"]]
    if missing_services:
        logger.error(f"Required services unavailable for chat: {missing_services}")
        raise HTTPException(status_code=503, detail=f"Required services unavailable: {missing_services}")
    
    try:
        # Get retriever for the requested collection
        collection_name = request.collection or "default"
        
        # Check if collection exists
        if collection_name not in rag_manager_global.list_collections():
            # If collection doesn't exist but we have files, create it
            if request.collection and file_manager_global.list_files():
                logger.info(f"Creating new collection: {collection_name}")
                rag_manager_global.get_or_create_collection(collection_name)
            else:
                # Default to "default" collection if specified one doesn't exist
                collection_name = "default"
                if collection_name not in rag_manager_global.list_collections():
                    # Create default collection if it doesn't exist
                    rag_manager_global.get_or_create_collection(collection_name)
        
        # Create a simple response for now - in a real implementation, you would:
        # 1. Create a retriever tool for the collection
        # 2. Configure an agent with the tool
        # 3. Run the agent with the user's message and history
        
        message_id = str(uuid.uuid4())
        
        # For now, just echo the message with info about the collection
        # You should replace this with proper agent execution
        return {
            "message_id": message_id,
            "content": f"I received your message: '{request.message}'\n\nI would search in the '{collection_name}' collection to find relevant information. (This is a placeholder response - real agent integration coming soon!)",
            "sources": []
        }
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

# Optional: WebSocket endpoint for real-time chat
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with agents."""
    await websocket.accept()
    try:
        while True:
            # Receive and parse message
            data = await websocket.receive_json()
            
            # Extract message and collection
            message = data.get("message", "")
            collection = data.get("collection", "default")
            history = data.get("history", [])
            
            # Process similar to the /chat endpoint
            # Simple echo for now
            response = {
                "message_id": str(uuid.uuid4()),
                "content": f"WebSocket received: '{message}'\n\nThis is a placeholder response from the WebSocket endpoint.",
                "sources": []
            }
            
            # Send response back to client
            await websocket.send_json(response)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket chat: {e}")
        await websocket.close(code=1011, reason=f"Error: {str(e)}")

@app.get("/health",
        summary="Health Check",
        description="Checks if the API is running and core services are initialized.")
async def health_check(dependencies: Dict[str, bool] = Depends(get_service_dependencies)):
    """Basic health check endpoint."""
    services_status = "ok" if all([
        dependencies["env"],
        dependencies["llm_service"],
        dependencies["tool_registry"]
    ]) else "error"
    
    rag_status = "ok" if dependencies["rag_manager"] else "disabled"
    
    return {
        "status": "ok",
        "core_services_status": services_status,
        "rag_status": rag_status,
        "services": dependencies
    }

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)