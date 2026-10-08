# src/rag.py
import os
import glob
import chromadb
from chromadb.utils import embedding_functions
from config import settings

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

class RAGService:
    def __init__(self):
        # 1. 初始化向量数据库（持久化）
        self.client = chromadb.PersistentClient(path=settings.RAG_DB_PATH)

        # 2. 初始化 Embedding 模型（本地 BGE 中文模型）
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-zh-v1.5"
        )

        # 3. 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="ops_knowledge",
            embedding_function=self.emb_fn
        )

    def _chunk_text(self, text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
        """简单但实用的中文文本切分（按段落+长度切分）"""
        paragraphs = text.split('\n')
        chunks = []
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n"
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def build_knowledge_base(self):
        """从 rag_docs/ 目录加载文档，切分并存入向量库"""
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rag_docs')
        if not os.path.exists(docs_dir):
            print('[rag] 未找到 rag_docs 目录，跳过知识库构建')
            return

        all_chunks = []
        all_ids = []

        for filepath in glob.glob(os.path.join(docs_dir, '*.md')):
            filename = os.path.basename(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            chunks = self._chunk_text(content)
            for i, chunk in enumerate(chunks):
                # 把文件名也拼进去，增加检索命中率
                chunk_with_source = f"【来源: {filename}】\n{chunk}"
                all_chunks.append(chunk_with_source)
                all_ids.append(f"{filename}_{i}")

        if all_chunks:
            # 批量写入（覆盖旧的）
            # 注意：ChromaDB 的 upsert 需要较新版本，这里用简单的 add
            existing = self.collection.get()
            if existing['ids']:
                self.collection.delete(ids=existing['ids'])
            self.collection.add(documents=all_chunks, ids=all_ids)
            print(f'[rag] 知识库构建完成，共写入 {len(all_chunks)} 个文本块')

    def retrieve(self, query: str, k: int = 3) -> str:
        """检索核心逻辑"""
        if not query or self.collection.count() == 0:
            return "无历史相似案例。"
        try:
            res = self.collection.query(query_texts=[query], n_results=k)
            docs = res.get("documents", [[]])[0]
            if not docs:
                return "无历史相似案例。"
            return "\n---\n".join(docs)
        except Exception as e:
            print(f'[rag] 检索失败: {e}')
            return "无历史相似案例。"


rag_service = RAGService()