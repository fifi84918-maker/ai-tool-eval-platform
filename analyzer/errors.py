"""静态检测层错误类型。"""


class AnalyzerError(Exception):
    """静态检测层错误基类。

    注意：单条规则的可预期失败不应抛异常，而应产出 FAIL/NEED_INFO
    finding（pipeline 亦有兜底捕获）；本异常仅用于调用方式错误等编程错误。
    """
