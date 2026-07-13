#!/usr/bin/env python3
"""
generate-vectordb.py — Gera o Vector Database FAISS para BYOK

Lê arquivos markdown de um diretório, chunk e embed usando
sentence-transformers, e salva um índice FAISS + metadados no
formato esperado pelo OpenShift Lightspeed (spec.ols.rag).

Uso:
    python generate-vectordb.py \\
        --input-dir ./content/ \\
        --output-dir ./vector_db/output/ \\
        --embedding-model sentence-transformers/all-mpnet-base-v2 \\
        --dimension 768 \\
        --chunk-size 1000 \\
        --chunk-overlap 200

Saída:
    output-dir/
    ├── faiss_store.db        # FAISS index + docstore (SQLite)
    ├── metadata.json          # Metadados do índice
    └── index_config.yaml     # Configuração do índice
"""

import argparse
import glob
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gera Vector Database FAISS para BYOK do OpenShift Lightspeed"
    )
    parser.add_argument(
        "--input-dir", "-i",
        required=True,
        help="Diretório com arquivos .md de entrada"
    )
    parser.add_argument(
        "--output-dir", "-o",
        required=True,
        help="Diretório de saída (faiss_store.db + metadados)"
    )
    parser.add_argument(
        "--embedding-model", "-e",
        default="sentence-transformers/all-mpnet-base-v2",
        help="Modelo de embedding (default: all-mpnet-base-v2)"
    )
    parser.add_argument(
        "--dimension", "-d",
        type=int,
        default=768,
        help="Dimensão do embedding (default: 768 para mpnet-base-v2)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Tamanho do chunk em caracteres (default: 1000)"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Sobreposição entre chunks em caracteres (default: 200)"
    )
    return parser.parse_args()


def load_markdown_files(input_dir: str) -> list[dict]:
    """Carrega todos os arquivos .md do diretório de entrada."""
    files = sorted(glob.glob(os.path.join(input_dir, "*.md")))
    if not files:
        print(f"ERRO: Nenhum arquivo .md encontrado em {input_dir}")
        sys.exit(1)

    documents = []
    for fpath in files:
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            print(f"  ⚠ {fname}: arquivo vazio, ignorado")
            continue
        documents.append({
            "file": fname,
            "path": fpath,
            "content": content,
        })
        print(f"  ✓ {fname}: {len(content)} caracteres")

    print(f"\n  Total: {len(documents)} documentos carregados")
    return documents


def chunk_documents(
    documents: list[dict],
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    """
    Divide documentos em chunks com sobreposição.

    Usa langchain text splitters se disponível, senão usa
    splitter simples próprio.
    """
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n", ". ", " ", ""],
            length_function=len,
        )
        use_langchain = True
    except ImportError:
        use_langchain = False

    all_chunks = []
    for doc in documents:
        text = doc["content"]

        if use_langchain:
            texts = splitter.split_text(text)
        else:
            # Splitter simples próprio
            texts = []
            step = chunk_size - chunk_overlap
            i = 0
            while i < len(text):
                end = min(i + chunk_size, len(text))
                chunk = text[i:end]
                if len(chunk) > 50:  # Ignora chunks muito pequenos
                    texts.append(chunk)
                i += step

        for idx, chunk_text in enumerate(texts):
            chunk_id = hashlib.sha256(
                f"{doc['file']}:{idx}:{chunk_text[:50]}".encode()
            ).hexdigest()[:16]

            all_chunks.append({
                "chunk_id": chunk_id,
                "file": doc["file"],
                "text": chunk_text,
                "chunk_index": idx,
                "total_chunks": len(texts),
            })

    print(f"  ✓ {len(all_chunks)} chunks gerados")
    return all_chunks


def build_faiss_index(
    chunks: list[dict],
    embedding_model_name: str,
    dimension: int,
    output_dir: str,
) -> str:
    """
    Gera embeddings e constrói o índice FAISS.

    Retorna o caminho do arquivo faiss_store.db.
    """
    print(f"\n  Carregando modelo de embedding: {embedding_model_name}...")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(embedding_model_name)
    print(f"  Modelo carregado. Dimensão: {model.get_sentence_embedding_dimension()}")

    # Prepara textos para embedding
    texts = [chunk["text"] for chunk in chunks]

    print(f"  Gerando embeddings para {len(texts)} chunks...")
    # Batch embedding para performance
    batch_size = 32
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.append(embeddings)
        sys.stdout.write(f"\r    Progresso: {min(i + batch_size, len(texts))}/{len(texts)}")
        sys.stdout.flush()

    sys.stdout.write("\n")
    embeddings_matrix = np.vstack(all_embeddings)
    print(f"  ✓ Embeddings shape: {embeddings_matrix.shape}")

    # Constrói FAISS index
    import faiss

    actual_dim = embeddings_matrix.shape[1]
    print(f"  Construindo índice FAISS (dimensão={actual_dim})...")

    # Índice plano (exato) — default para BYOK
    index = faiss.IndexFlatIP(actual_dim)
    index.add(embeddings_matrix.astype(np.float32))
    print(f"  ✓ FAISS index: {index.ntotal} vetores")

    # Salva o índice e docstore em SQLite (formato compatível com OLS)
    os.makedirs(output_dir, exist_ok=True)

    # Cria o banco FAISS + docstore
    faiss_store_path = os.path.join(output_dir, "faiss_store.db")

    import sqlite3
    import pickle

    conn = sqlite3.connect(faiss_store_path)
    cursor = conn.cursor()

    # Tabela do índice FAISS (serializado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faiss_index (
            id INTEGER PRIMARY KEY,
            vector_data BLOB
        )
    """)

    # Serializa o índice FAISS (API padrão FAISS >= 1.7)
    faiss_bytes = faiss.serialize_index(index)
    cursor.execute(
        "INSERT OR REPLACE INTO faiss_index (id, vector_data) VALUES (1, ?)",
        (faiss_bytes,)
    )

    # Tabela de documentos (chunks)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docstore (
            chunk_id TEXT PRIMARY KEY,
            file TEXT,
            text TEXT,
            chunk_index INTEGER,
            total_chunks INTEGER,
            embedding BLOB
        )
    """)

    for chunk, emb in zip(chunks, embeddings_matrix):
        cursor.execute(
            """INSERT OR REPLACE INTO docstore
               (chunk_id, file, text, chunk_index, total_chunks, embedding)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                chunk["chunk_id"],
                chunk["file"],
                chunk["text"],
                chunk["chunk_index"],
                chunk["total_chunks"],
                pickle.dumps(emb.astype(np.float32)),
            )
        )

    # Tabela de metadados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    vector_db_id = f"byok-{uuid.uuid4().hex[:8]}"
    metadata_rows = [
        ("vector_db_id", vector_db_id),
        ("embedding_model", embedding_model_name),
        ("dimension", str(actual_dim)),
        ("num_chunks", str(len(chunks))),
        ("num_documents", str(len(set(c["file"] for c in chunks)))),
    ]
    cursor.executemany(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        metadata_rows,
    )

    conn.commit()
    conn.close()

    print(f"  ✓ faiss_store.db salvo em: {faiss_store_path}")
    return faiss_store_path, vector_db_id


def save_metadata(output_dir: str, vector_db_id: str, args, num_chunks: int):
    """Salva metadados em JSON para referência."""
    metadata = {
        "vector_db_id": vector_db_id,
        "embedding_model": args.embedding_model,
        "dimension": args.dimension,
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "num_chunks": num_chunks,
        "created_by": "generate-vectordb.py",
        "rag_path": "/rag/vector_db",
    }

    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"  ✓ metadata.json salvo: {metadata_path}")

    # Também salva yaml-style config para compatibilidade
    config_lines = [
        f"vector_db_id: {vector_db_id}",
        f"embedding_model: {args.embedding_model}",
        f"dimension: {args.dimension}",
        f"num_chunks: {num_chunks}",
    ]
    config_path = os.path.join(output_dir, "index_config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("\n".join(config_lines) + "\n")
    print(f"  ✓ index_config.yaml salvo: {config_path}")


def main():
    args = parse_args()

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)

    print("=" * 55)
    print("  BYOK Vector Database Generator - OpenShift Lightspeed")
    print("=" * 55)
    print(f"\n  Input:  {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Model:  {args.embedding_model}")
    print(f"  Chunk:  {args.chunk_size} / overlap {args.chunk_overlap}")
    print()

    # 1. Carregar documentos
    print("[1/4] Carregando documentos...")
    docs = load_markdown_files(input_dir)

    # 2. Chunk
    print("\n[2/4] Chunking documentos...")
    chunks = chunk_documents(docs, args.chunk_size, args.chunk_overlap)

    # 3. Embeddings + FAISS
    print("\n[3/4] Gerando embeddings e índice FAISS...")
    faiss_path, vector_db_id = build_faiss_index(
        chunks, args.embedding_model, args.dimension, output_dir
    )

    # 4. Metadados
    print("\n[4/4] Salvando metadados...")
    save_metadata(output_dir, vector_db_id, args, len(chunks))

    print()
    print("=" * 55)
    print("  ✓ BYOK Vector Database gerado com sucesso!")
    print(f"  Vector DB ID: {vector_db_id}")
    print(f"  Caminho:     {faiss_path}")
    print("=" * 55)
    print()
    print("  Para usar no OpenShift Lightspeed, faça:")
    print(f"    1. Crie a imagem: podman build -t byok-image:latest")
    print("    2. Push para seu registry")
    print("    3. Configure no OLSConfig:")
    print("       spec.ols.rag:")
    print(f"         - image: <registry>/byok-image:latest")
    print(f"           indexID: {vector_db_id}")
    print("           indexPath: /rag/vector_db")
    print()


if __name__ == "__main__":
    main()
