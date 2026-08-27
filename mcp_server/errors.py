"""MCP 层错误：工具 handler 抛出，server 转结构化 error 响应。"""


class McpToolError(Exception):
    """工具执行错误；code 供客户端程序化处理。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_payload(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}
