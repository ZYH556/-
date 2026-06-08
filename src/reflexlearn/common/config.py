from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://reflexlearn:reflexlearn@127.0.0.1:15432/reflexlearn"
    redis_url: str = "redis://127.0.0.1:16379/0"
    qdrant_url: str = "http://127.0.0.1:16333"
    neo4j_uri: str = "bolt://127.0.0.1:17687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "reflexlearn"

    deepseek_api_key: str = ""
    qwen_api_key: str = ""
    anthropic_api_key: str = ""

    kafka_bootstrap_servers: str = "127.0.0.1:19092"

    enable_reflexion: bool = True
    enable_rerank: bool = True
    enable_graph_retrieval: bool = False
    enable_kafka: bool = False
    enable_rag: bool = True

    # —— 三级记忆 / 多轮会话（6.2）——
    enable_multi_turn: bool = True       # kill-switch：False 即彻底退化单轮（跳过 Redis load/persist）
    session_ttl: int = 7200              # Redis session:{sid} TTL 秒（docs §7 = 2h）
    summary_model: str = ""              # summary 任务显式模型覆盖（空 = 按 provider 自动选便宜档）
    summary_recent_turns: int = 6        # trim 保留最近 N 轮原文
    context_max_chars: int = 6000        # trim 总字符预算
    summary_max_layer_chars: int = 800   # 递归摘要单层字符上限
    summary_max_depth: int = 3           # 递归摘要最大层数

    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    knowledge_collection: str = "knowledge_chunks"
    retrieve_top_k: int = 5

    # —— M4 数据工程 / 写链路 ——
    enable_contextual: bool = False      # 上传时为每 chunk 生成 LLM 定位摘要（contextual retrieval）；
                                         # 默认关：每 chunk 一次 LLM，大文档串行会显著拉长上传时延
    contextual_max_chunks: int = 50      # 开启 contextual 时的 chunk 上限，超过则整体跳过摘要（控成本）

    enable_graph_build: bool = False     # 上传时 LLM 抽取概念/关系入 Neo4j（M4-B 写侧；读侧是 enable_graph_retrieval）
    graph_extract_max_chars: int = 8000  # 图谱抽取输入文本上限（文档级一次 LLM 调用，超长截断控成本）

    # —— M4-D MinIO 原始存储 + Spark/批清洗 ——
    enable_minio: bool = False           # 是否用 MinIO 原始存储（缺服务降级）
    minio_endpoint: str = "127.0.0.1:19000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "reflexlearn-raw"
    minio_secure: bool = False
    clean_min_chars: int = 30            # 批清洗质量过滤：内容短于此视为噪声丢弃（docs §6.1 取 100，小语料放宽）

    # —— M4-E 多模态视频（SeeDance）——
    enable_seedance: bool = False        # 视频作业是否调真实 SeeDance（关闭 / 无 key → 降级 storyboard 占位）
    seedance_api_key: str = ""           # 火山方舟 ARK API key（SeeDance 视频生成）
    seedance_model: str = "doubao-seedance-1-0-pro-250528"
    seedance_endpoint: str = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
    video_job_ttl: int = 86400           # Redis video_job:{id} TTL 秒（默认 1 天）

    # P0 security baseline: auth / CORS / upload limits
    app_env: str = "development"
    auth_enabled: bool = True
    auth_secret_key: str = "dev-only-change-me-reflexlearn-auth-secret"
    auth_token_ttl_seconds: int = 7200
    auth_issuer: str = "reflexlearn"
    auth_audience: str = "reflexlearn-web"
    auth_demo_username: str = "admin"
    auth_demo_password: str = "reflexlearn-admin"
    auth_demo_tenant_id: str = "default"
    auth_demo_role: str = "admin"

    cors_allow_origins: str = (
        "http://localhost:3000,http://localhost:3001,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001"
    )
    trusted_hosts: str = "127.0.0.1,localhost,testserver"

    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_upload_extensions: str = "pdf,docx,pptx,html,htm,md,txt"
    allowed_upload_mime_types: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.openxmlformats-officedocument.presentationml.presentation,"
        "text/html,text/markdown,text/plain"
    )

    max_iterations: int = 20
    max_replan: int = 3
    token_budget: int = 50000
    max_react_steps: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
