#!/usr/bin/env python3
"""Indexador BYOK - Red Hat Connectivity Link para Lightspeed Core.

Gera um vector database FAISS a partir dos documentos markdown no diretório
byok/content/, usando o modelo de embedding sentence-transformers/all-mpnet-base-v2.

Uso:
  uv run python byok-processor.py -f ../content -o ../vector_db/output -i rh-connectivity-link
"""

import argparse
import os
import shutil
import tempfile

from lightspeed_rag_content.document_processor import DocumentProcessor
from lightspeed_rag_content.metadata_processor import MetadataProcessor


class CustomMetadataProcessor(MetadataProcessor):
    """Metadata processor para documentos do Red Hat Connectivity Link."""

    def __init__(self, hermetic_build=False):
        super().__init__(hermetic_build=hermetic_build)
        self.base_url = "https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/"

    def url_function(self, file_path: str) -> str:
        """Retorna URL de referencia para o documento."""
        filename = os.path.basename(file_path)
        url_map = {
            "01-overview.md": "/html/introduction_to_connectivity_link/about-connectivity-link_rhcl",
            "02-architecture.md": "/html/introduction_to_connectivity_link/about-connectivity-link_rhcl",
            "03-installation.md": "/html/install/index",
            "04-gateway-api.md": "/html/configure/index",
            "05-tls-policies.md": "/html/configure/index",
            "06-auth-policies.md": "/html/configure/index",
            "07-rate-limiting.md": "/html/configure/index",
            "08-dns-multicluster.md": "/html/configure/index",
            "09-observability.md": "/html/operate/index",
        }
        suffix = url_map.get(filename, "")
        return f"{self.base_url}{suffix}" if suffix else self.base_url

    def title_function(self, file_path: str) -> str:
        """Retorna titulo do documento baseado no nome do arquivo."""
        filename = os.path.basename(file_path)
        title_map = {
            "01-overview.md": "Red Hat Connectivity Link - Overview",
            "02-architecture.md": "Red Hat Connectivity Link - Architecture",
            "03-installation.md": "Red Hat Connectivity Link - Installation",
            "04-gateway-api.md": "Red Hat Connectivity Link - Gateway API",
            "05-tls-policies.md": "Red Hat Connectivity Link - TLS Policies",
            "06-auth-policies.md": "Red Hat Connectivity Link - Auth Policies",
            "07-rate-limiting.md": "Red Hat Connectivity Link - Rate Limiting",
            "08-dns-multicluster.md": "Red Hat Connectivity Link - DNS and Multicluster",
            "09-observability.md": "Red Hat Connectivity Link - Observability",
        }
        return title_map.get(filename, "Red Hat Connectivity Link Documentation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexa documentos BYOK do Connectivity Link")
    parser.add_argument("-f", "--folder", required=True, help="Diretorio com documentos markdown")
    parser.add_argument("-o", "--output", required=True, help="Diretorio de saida para vector DB")
    parser.add_argument("-i", "--index", required=True, help="Nome do indice (vector_db_id)")
    parser.add_argument("-m", "--model-name", default="sentence-transformers/all-mpnet-base-v2", help="Modelo de embedding")
    parser.add_argument("-d", "--model-dir", default="", help="Diretorio do modelo de embedding")
    parser.add_argument("-c", "--chunk-size", type=int, default=1000, help="Tamanho do chunk em tokens")
    parser.add_argument("-v", "--chunk-overlap", type=int, default=200, help="Overlap entre chunks")
    parser.add_argument("-s", "--vector-store", default="llamastack-faiss", help="Tipo de vector store (faiss, llamastack-faiss)")
    parser.add_argument("--hermetic", action="store_true", help="Build hermetico (offline)")
    args = parser.parse_args()

    print(f"=== Indexacao BYOK - Red Hat Connectivity Link ===")
    print(f"Documentos:     {args.folder}")
    print(f"Saida:          {args.output}")
    print(f"Indice:         {args.index}")
    print(f"Modelo:         {args.model_name}")
    print(f"Vector Store:   {args.vector_store}")
    print(f"Chunk:          {args.chunk_size} (overlap: {args.chunk_overlap})")
    print()

    metadata_processor = CustomMetadataProcessor(hermetic_build=args.hermetic)

    document_processor = DocumentProcessor(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        model_name=args.model_name,
        embeddings_model_dir=args.model_dir if args.model_dir else None,
        vector_store_type=args.vector_store,
        doc_type="markdown",
        show_progress=True,
    )

    print("[1/2] Copiando documentos para diretorio temporario...")
    tmpdir = tempfile.mkdtemp(prefix="byok-content-")
    try:
        for fname in sorted(os.listdir(args.folder)):
            if fname.endswith(".md"):
                shutil.copy2(os.path.join(args.folder, fname), os.path.join(tmpdir, fname))

        print("[2/2] Processando documentos e gerando vector database...")
        document_processor.process(
            docs_dir=tmpdir,
            metadata=metadata_processor,
            required_exts=[".md"],
        )

        document_processor.save(index=args.index, output_dir=args.output)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print()
    print("=== Indexacao concluida! ===")
    print(f"Vector DB: {args.output}/")
    print(f"Index ID:  {args.index}")
    print()
    print("Configure o lightspeed-stack.yaml com:")
    print(f"  rag_id:           {args.index}")
    print(f"  vector_db_id:     {args.index}")
    if args.vector_store == "llamastack-faiss":
        print(f"  db_path:          {args.output}/faiss_store.db")
    else:
        print(f"  db_path:          {args.output}/")
