"""
Builds LaTeX from parsed resume dict.
- Fixed template matching the user's original resume style
- Approved + ML keywords injected into the most relevant skills category line
- Projects rendered as bold title + bullet list (same style as original)
- Returns (latex_str, change_log)
- Zero LLM involvement — deterministic
"""
import re

_TEMPLATE = r"""
\documentclass[10pt, letterpaper]{article}
\usepackage[top=0.5in, bottom=0.5in, left=0.7in, right=0.7in]{geometry}
\usepackage{fontspec}
\setmainfont{Cambria}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{titlesec}
\usepackage{setspace}
\hypersetup{colorlinks=true, urlcolor=blue, linkcolor=blue, filecolor=blue}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{2pt}

%% Section style: UPPERCASE bold, thin rule below — matches original resume
\titleformat{\section}{\large\bfseries}{}{0em}{\MakeUppercase}[\vspace{-4pt}\rule{\textwidth}{0.5pt}]
\titlespacing{\section}{0pt}{8pt}{4pt}

\begin{document}

%%HEADER%%

%%SUMMARY_SECTION%%

%%SKILLS_SECTION%%

%%EXPERIENCE_SECTION%%

%%PROJECTS_SECTION%%

%%EDUCATION_SECTION%%

%%CERT_SECTION%%

%%EXTRA_SECTIONS%%

\end{document}
"""

# ---------------------------------------------------------------------------
# Affinity map: (list_of_seed_fragments, list_of_category_words_to_match)
# When a keyword matches any seed, we place it on the first skills line
# that contains any of the category words (case-insensitive).
# ---------------------------------------------------------------------------
_AFFINITY_MAP = [
    # Languages
    (
        ["python", "java", "scala", "golang", "ruby", "bash", "shell", "r,",
         "julia", "matlab", "typescript", "javascript", "c++", "c#", "c programming",
         "systems programming", "rest api", "fastapi", "flask", "django", "rest",
         "programming languages", "data structures", "algorithms",
         "object-oriented", "functional programming", "concurrent programming"],
        ["language"],
    ),
    # Machine Learning & Deep Learning
    (
        ["supervised", "unsupervised", "reinforcement learning", "semi-supervised",
         "self-supervised", "transfer learning", "few-shot", "zero-shot",
         "contrastive learning", "metric learning", "active learning", "federated",
         "continual learning", "meta-learning", "ensemble", "boosting", "bagging",
         "random forest", "gradient boosting", "decision tree", "clustering",
         "k-means", "dbscan", "pca", "t-sne", "umap", "regression", "classification",
         "anomaly detection", "time series", "recommendation", "collaborative filtering",
         "data mining", "ml-based", "multimodal learning", "sensor fusion",
         "autonomous driving", "embodied ai", "deep learning", "neural",
         "cnn", "rnn", "lstm", "gru", "attention", "bert", "gpt", "t5",
         "diffusion", "gan", "vae", "hypothesis testing", "statistical modeling",
         "feature engineering", "data augmentation", "pandas", "numpy", "scipy",
         "hyperparameter tuning", "automl", "cross-validation",
         "ml accelerators", "deep-learning systems software", "model optimization",
         "training infrastructure"],
        ["machine learning", "deep learning", "ml"],
    ),
    # Frameworks & Libraries
    (
        ["pytorch", "tensorflow", "keras", "jax", "flax", "scikit-learn", "sklearn",
         "hugging face", "transformers", "diffusers", "spacy", "nltk", "gensim",
         "xgboost", "lightgbm", "catboost", "opencv", "pillow", "albumentations",
         "fastai", "onnx", "openvino"],
        ["framework", "librar"],
    ),
    # Generative AI / LLMs
    (
        ["langchain", "llamaindex", "langgraph", "llm", "rag",
         "retrieval augmented", "prompt engineering", "generative ai",
         "embedding", "vector database", "vector search", "vector store",
         "faiss", "pinecone", "weaviate", "semantic search",
         "agentic", "chain of thought", "autonomous reasoning", "llm-based",
         "fine-tuning", "instruction tuning", "rlhf", "dpo", "peft", "lora",
         "multimodal model", "vision language"],
        ["generative", "llm", "rag", "llms"],
    ),
    # GPU / Hardware acceleration + compiler/systems ML
    (
        ["cuda", "cudnn", "gpu", "gpu training", "mixed precision", "fp16", "bf16",
         "tensorrt", "distributed training", "ddp", "deepspeed", "fsdp",
         "gradient checkpointing", "flash attention", "amp", "multi-gpu",
         "quantization", "int8", "vllm", "llm inference", "inference optimization",
         "lora", "qlora", "peft", "rlhf", "dpo", "knowledge distillation",
         "model distillation", "pruning", "model compression",
         "ai accelerators", "ml accelerators", "compilers", "compiler",
         "llvm", "mlir", "xla", "torchscript", "jit", "op fusion",
         "building models", "model building", "training models",
         "hpc", "high performance computing", "parallel computing"],
        ["machine learning", "deep learning", "framework", "librar"],
    ),
    # MLOps & Deployment
    (
        ["docker", "kubernetes", "mlflow", "airflow", "kubeflow", "ci/cd",
         "devops", "github actions", "jenkins", "prefect", "dagster",
         "torchserve", "triton", "tf serving", "bentoml", "ray serve",
         "model serving", "model deployment", "model monitoring", "data drift",
         "model versioning", "a/b testing", "unit testing", "integration testing",
         "testing", "mlops", "pipeline", "orchestration"],
        ["mlops", "deployment", "devops"],
    ),
    # Cloud Platforms
    (
        ["aws", "azure", "gcp", "sagemaker", "vertex ai", "google cloud",
         "lambda", "ec2", "s3", "eks", "ecs", "azure ml", "data factory",
         "cloud computing", "serverless", "bedrock",
         "inferentia", "trainium", "aws inferentia", "aws trainium",
         "amazon inferentia", "amazon trainium"],
        ["cloud"],
    ),
    # Databases & Storage
    (
        ["sql", "postgresql", "mysql", "mongodb", "nosql", "elasticsearch",
         "redis", "cassandra", "spark", "hadoop", "kafka", "etl",
         "data pipeline", "data warehouse", "dbt", "feature store",
         "data lake", "databricks", "snowflake", "bigquery"],
        ["database", "storage"],
    ),
    # Visualization & BI
    (
        ["matplotlib", "seaborn", "plotly", "tableau", "power bi", "powerbi",
         "bokeh", "dash", "streamlit", "grafana", "kibana"],
        ["visualiz", "bi"],
    ),
    # Mathematics & Statistics
    (
        ["statistics", "probability", "linear algebra", "calculus", "optimization",
         "bayesian", "mathematics", "discrete math"],
        ["mathematic", "statistic"],
    ),
    # Domain Expertise — catch-all for analysis, program synthesis, etc.
    (
        ["nlp", "natural language processing", "computer vision", "real-time",
         "time series forecasting", "anomaly", "recommendation systems",
         "point cloud", "lidar", "robotics", "autonomous",
         "computer science", "real-time decision", "decision-making",
         "signal processing", "optimization", "operations research",
         "program analysis", "program analyzers", "program synthesis",
         "program synthesis engines", "fuzz testing", "fuzzing",
         "static analysis", "dynamic analysis", "code analysis"],
        ["domain expertise"],
    ),
]


def _strip_latex(text: str) -> str:
    """Remove LaTeX commands for plain-text comparison."""
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    return text.lower()


def _find_target_line(kw: str, skills: list[str]) -> int | None:
    """Return index of best matching skills line for this keyword."""
    kl = kw.lower().strip()
    for seeds, cats in _AFFINITY_MAP:
        matched = any(seed in kl or kl in seed for seed in seeds)
        if matched:
            for i, line in enumerate(skills):
                plain = _strip_latex(line)
                if any(cat in plain for cat in cats):
                    return i
    return None


# Common abbreviation ↔ full-form pairs for ATS-aware duplicate detection
_SYNONYMS: dict[str, list[str]] = {
    "ml":  ["machine learning"],
    "dl":  ["deep learning"],
    "nlp": ["natural language processing"],
    "cv":  ["computer vision"],
    "rl":  ["reinforcement learning"],
    "llm": ["large language model", "large language models"],
    "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
    "ai":  ["artificial intelligence"],
    "nn":  ["neural network", "neural networks"],
    "ml algorithms": ["machine learning"],
    "ml models": ["machine learning"],
    "machine learning algorithms": ["machine learning"],
}


def _already_covered(kw: str, combined: str) -> bool:
    """True if kw or any of its synonyms already appear in combined skills text."""
    kl = kw.lower()
    if kl in combined:
        return True
    for abbrev, expansions in _SYNONYMS.items():
        if kl == abbrev and any(exp in combined for exp in expansions):
            return True
        if kl in expansions and abbrev in combined:
            return True
    return False


def _closest_line(kw: str, skills: list[str]) -> int:
    """
    Fallback: find the existing skills line most similar to kw by word overlap.
    Prefers the Domain Expertise line (most general catch-all).
    Falls back to the line with the most shared words, then the last line.
    """
    kw_words = set(kw.lower().split())
    best_idx = len(skills) - 1
    best_score = -1
    domain_idx = -1

    for i, line in enumerate(skills):
        plain = _strip_latex(line)
        if "domain" in plain:
            domain_idx = i
        score = len(kw_words & set(plain.split()))
        if score > best_score:
            best_score = score
            best_idx = i

    # Prefer domain expertise for things with no obvious match
    if best_score == 0 and domain_idx >= 0:
        return domain_idx
    return best_idx


def _inject_with_log(
    skills: list[str],
    kw_with_source: list[tuple[str, str]],
) -> tuple[list[str], list[dict], list[dict]]:
    """
    Inject keywords into the right skill lines.
    Returns (updated_skills, added_log, already_present_log).
    """
    combined = " ".join(_strip_latex(s) for s in skills)
    result = list(skills)
    added: list[dict] = []
    already: list[dict] = []
    leftovers: list[tuple[str, str]] = []

    for kw, source in kw_with_source:
        if _already_covered(kw, combined):
            already.append({"skill": kw, "source": source,
                            "reason": "Already listed in your Technical Skills section (or covered by a synonym)"})
            continue

        idx = _find_target_line(kw, result)
        if idx is not None:
            plain = _strip_latex(result[idx])
            cat_name = plain.split(":")[0].strip().title() if ":" in plain else "Technical Skills"
            result[idx] = result[idx].rstrip() + ", " + kw
            combined += " " + kw.lower()
            added.append({"skill": kw, "source": source, "category": cat_name})
        else:
            leftovers.append((kw, source))

    # No "Other Technical Skills" label — merge leftovers into the closest existing line
    for kw, source in leftovers:
        idx = _closest_line(kw, result)
        plain = _strip_latex(result[idx])
        cat_name = plain.split(":")[0].strip().title() if ":" in plain else "Technical Skills"
        result[idx] = result[idx].rstrip() + ", " + kw
        combined += " " + kw.lower()
        added.append({"skill": kw, "source": source, "category": cat_name})

    return result, added, already


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _header(parsed: dict) -> str:
    lines = [r"\begin{center}", rf"{{\LARGE\bfseries {parsed['name']}}}\\[2pt]"]
    if parsed.get("title"):
        lines.append(rf"{parsed['title']}\\[2pt]")
    if parsed.get("contact"):
        lines.append(parsed["contact"])
    lines.append(r"\end{center}")
    return "\n".join(lines)


def _summary_section(parsed: dict) -> str:
    if not parsed.get("summary"):
        return ""
    return "\\section{Professional Summary}\n" + parsed["summary"]


def _skills_section(skills: list[str]) -> str:
    if not skills:
        return ""
    items = "\n".join(f"  \\item {line}" for line in skills)
    return (
        "\\section{Technical Skills}\n"
        "\\begin{itemize}[noitemsep, topsep=2pt, leftmargin=*]\n"
        + items
        + "\n\\end{itemize}"
    )


def _titled_section(section_title: str, items: list[dict], bold_header: bool = False) -> str:
    """
    Render experience-like or projects-like section.
    bold_header=True wraps project titles in \\textbf{}.
    """
    if not items:
        return ""
    blocks = []
    for item in items:
        header = item["header_latex"]
        if bold_header and not header.startswith("\\textbf{"):
            header = f"\\textbf{{{header}}}"
        bullets = item.get("bullets", [])
        block = header
        if bullets:
            bullet_lines = "\n".join(f"  \\item {b}" for b in bullets)
            block += (
                "\n\\begin{itemize}[noitemsep, topsep=2pt, leftmargin=*]\n"
                + bullet_lines
                + "\n\\end{itemize}"
            )
        blocks.append(block)
    return f"\\section{{{section_title}}}\n" + "\n\n".join(blocks)


def _education_section(parsed: dict) -> str:
    edu = parsed.get("education", [])
    if not edu:
        return ""
    return "\\section{Education}\n" + "\n\n".join(edu)


def _cert_section(parsed: dict) -> str:
    certs = parsed.get("certifications", [])
    if not certs:
        return ""
    items = "\n".join(f"  \\item {c}" for c in certs)
    return (
        "\\section{Certifications}\n"
        "\\begin{itemize}[noitemsep, topsep=2pt, leftmargin=*]\n"
        + items
        + "\n\\end{itemize}"
    )


def _extra_sections(parsed: dict) -> str:
    extras = parsed.get("extra_sections", [])
    if not extras:
        return ""
    blocks = []
    for sec in extras:
        lines = "\n\n".join(sec["lines"])
        blocks.append(f"\\section{{{sec['title']}}}\n{lines}")
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build(
    parsed: dict,
    tagged_keywords: list[tuple[str, str]],  # [(skill, source_label)]
) -> tuple[str, dict]:
    """
    Build complete LaTeX document.
    Returns (latex_source, change_log).
    change_log = {"added": [...], "already_present": [...]}
    """
    kw_with_source: list[tuple[str, str]] = tagged_keywords

    updated_skills, added_log, already_log = _inject_with_log(
        list(parsed.get("skills", [])), kw_with_source
    )

    latex = _TEMPLATE
    latex = latex.replace("%%HEADER%%",             _header(parsed))
    latex = latex.replace("%%SUMMARY_SECTION%%",    _summary_section(parsed))
    latex = latex.replace("%%SKILLS_SECTION%%",     _skills_section(updated_skills))
    latex = latex.replace("%%EXPERIENCE_SECTION%%", _titled_section("Professional Experience", parsed.get("experience", []), bold_header=False))
    latex = latex.replace("%%PROJECTS_SECTION%%",   _titled_section("Projects", parsed.get("projects", []), bold_header=True))
    latex = latex.replace("%%EDUCATION_SECTION%%",  _education_section(parsed))
    latex = latex.replace("%%CERT_SECTION%%",       _cert_section(parsed))
    latex = latex.replace("%%EXTRA_SECTIONS%%",     _extra_sections(parsed))

    return latex, {"added": added_log, "already_present": already_log}
