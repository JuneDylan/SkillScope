"""
共享正则模式与安全规则库 v3.0
增强：规则结构化、支持元数据扩展、40+ 规则覆盖
"""
from __future__ import annotations

SECRET_PATTERNS = {
    "openai_api_key": {
        "pattern": r"sk-[a-zA-Z0-9]{48,}",
        "example": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "severity": "critical",
    },
    "anthropic_api_key": {
        "pattern": r"sk-ant-[a-zA-Z0-9]{32,}",
        "example": "sk-ant-xxxxx",
        "severity": "critical",
    },
    "generic_api_key": {
        "pattern": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*[\"']?[a-zA-Z0-9_-]{16,}[\"']?",
        "example": "api_key = abc123...",
        "severity": "critical",
    },
    "password_literal": {
        "pattern": r"(?i)(password|passwd|pwd)\s*[:=]\s*[\"'][^\"']{8,}[\"']",
        "example": "password = 'secret123'",
        "severity": "warning",
    },
    "aws_access_key": {
        "pattern": r"AKIA[0-9A-Z]{16}",
        "example": "AKIAxxxxxxxxxxxxxxxx",
        "severity": "critical",
    },
    "github_token": {
        "pattern": r"gh[pousr]_[A-Za-z0-9_]{36,}",
        "example": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "severity": "critical",
    },
    "jwt_token": {
        "pattern": r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}",
        "example": "eyJhbGciOiJIUzI1NiIs...",
        "severity": "critical",
    },
    "private_key_block": {
        "pattern": r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----",
        "example": "-----BEGIN RSA PRIVATE KEY-----",
        "severity": "critical",
    },
    "slack_token": {
        "pattern": r"xox[baprs]-[0-9a-zA-Z-]{10,}",
        "example": "xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx",
        "severity": "critical",
    },
    "stripe_key": {
        "pattern": r"(?:sk|pk)_(?:test|live)_[a-zA-Z0-9]{24,}",
        "example": "sk_live_xxxxxxxxxxxxxxxxxxxxxx",
        "severity": "critical",
    },
    "google_api_key": {
        "pattern": r"AIza[0-9A-Za-z_-]{35}",
        "example": "AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "severity": "critical",
    },
    "slack_webhook": {
        "pattern": r"https://hooks\.slack\.com/services/T[a-zA-Z0-9]+/B[a-zA-Z0-9]+/[a-zA-Z0-9]+",
        "example": "https://hooks.slack.com/services/T.../B.../xxx",
        "severity": "critical",
    },
}

DANGEROUS_FUNCTIONS = [
    (r"\beval\s*\(", "eval() 调用存在代码注入风险"),
    (r"\bexec\s*\(", "exec() 调用存在代码注入风险"),
    (r"\bos\.system\s*\(", "os.system() 调用存在命令注入风险"),
    (r"\bsubprocess\.call\s*\(", "subprocess.call() 可能存在命令注入风险"),
    (r"\bsubprocess\.run\s*\(", "subprocess.run() 可能存在命令注入风险"),
    (r"\bsubprocess\.Popen\s*\(", "subprocess.Popen() 可能存在命令注入风险"),
    (r"\binput\s*\(", "input() 直接获取用户输入，需验证"),
    (r"\bpickle\.loads\s*\(", "pickle.loads() 反序列化不可信数据存在远程代码执行风险"),
    (r"\bpickle\.load\s*\(", "pickle.load() 从文件反序列化存在远程代码执行风险"),
    (r"\byaml\.load\s*\(", "yaml.load() 未指定 Loader 存在反序列化风险，应使用 yaml.safe_load()"),
    (r"\bmarshal\.loads\s*\(", "marshal.loads() 反序列化不可信数据存在安全风险"),
    (r"\b__import__\s*\(", "__import__() 动态导入存在代码注入风险"),
    (r"\bcompile\s*\(", "compile() 动态编译代码存在注入风险"),
    (r"\bshelve\.open\s*\(", "shelve.open() 使用 pickle 序列化，存在反序列化风险"),
]

PROMPT_INJECTION_PATTERNS = [
    (
        r'f[\'"].*\{.*(?:user|input|query|prompt|content|message|text|msg).*\}.*[\'"]',
        "f-string 中直接拼接用户输入变量，存在 Prompt 注入风险",
        "critical",
    ),
    (
        r'\.format\s*\(.*(?:user|input|query|prompt|content|message|text|msg)',
        "使用 .format() 拼接用户输入，建议改为参数化调用",
        "warning",
    ),
    (
        r'%\s*(?:user|input|query|prompt|content|message|text|msg)',
        "使用 % 格式化拼接用户输入，建议改为参数化调用",
        "warning",
    ),
    (
        r'[\'"].*\+\s*(?:user|input|query|prompt|content|message|text|msg)',
        "使用字符串拼接用户输入，存在 Prompt 注入风险",
        "critical",
    ),
    (
        r'Jinja2?\s*\(|\.render\s*\(|Template\s*\(',
        "使用模板引擎渲染用户输入，存在模板注入 (SSTI) 风险",
        "warning",
    ),
]

VENDOR_SPECIFIC_APIS = [
    (r"\bfunctions\s*=", "使用了 OpenAI 特有的 functions 参数"),
    (r"\btool_choice\s*=", "使用了 OpenAI 特有的 tool_choice 参数"),
    (r"\bresponse_format\s*=\s*\{\s*[\"']type[\"']\s*:\s*[\"']json_schema[\"']", "使用了 OpenAI 特有的 json_schema 响应格式"),
    (r"\btop_k\s*=", "使用了 Claude 特有的 top_k 参数"),
    (r"\bazure_endpoint\s*=", "使用了 Azure OpenAI 特有端点配置"),
    (r"\bbedrock-runtime\b", "使用了 AWS Bedrock 特有运行时"),
    (r"\bvertexai\b", "使用了 Google Vertex AI 特有 SDK"),
]

INSECURE_NETWORK_PATTERNS = [
    (r'http://[^\s\'"]+(?:api|auth|login|token|key)', "使用 HTTP 明文传输敏感数据，存在中间人攻击风险"),
    (r'verify\s*=\s*False', "禁用了 SSL 证书验证，存在中间人攻击风险"),
    (r'ssl\._create_unverified_context', "创建未验证的 SSL 上下文，存在安全风险"),
]

LOGGING_SENSITIVE_PATTERNS = [
    (r'logging\.\w+\(.*(?:password|token|secret|key|credential)', "日志中可能包含敏感信息"),
    (r'print\s*\(.*(?:password|token|secret|api_key|credential)', "print 输出可能泄露敏感信息"),
]

RESOURCE_CLEANUP_PATTERNS = [
    (r'\bopen\s*\([^)]+\)(?![^]*\bwith\b)', "文件操作未使用 with 语句，可能导致资源泄露"),
]

ENCODING_PATTERNS = [
    (r'\.read\(\)(?!\s*encoding)', "文件读取未指定编码，可能在跨平台时出现编码问题"),
    (r'\.read_text\(\)(?!\s*encoding)', "read_text() 未指定编码，建议显式指定 encoding='utf-8'"),
]
