"""稳定 ID / SHA-256 纯函数。不读文件、不依赖外部库、无副作用。"""

import hashlib


def sha256_hex(data: bytes | str) -> str:
    """返回输入的 SHA-256 十六进制摘要；str 按 UTF-8 编码。"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def stable_skill_id(source_kind: str, source_object_id: str) -> str:
    """由来源类型 + 来源对象 ID 派生平台内稳定 ID（确定性，同输入同输出）。"""
    return sha256_hex(f"{source_kind}\x00{source_object_id}")


def dir_hash(entries: list[tuple[str, str]]) -> str:
    """Skill 目录归一化哈希（去重层级 2，PRD 7.4）。

    entries 为 (归一化相对路径, 文件内容 sha256_hex) 列表；本函数只做
    确定性聚合（按路径排序后拼接再哈希），路径归一化由调用方负责。
    """
    joined = "\x00".join(f"{path}\x01{digest}" for path, digest in sorted(entries))
    return sha256_hex(joined)
