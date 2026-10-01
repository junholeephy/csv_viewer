"""루트 디렉터리 아래의 데이터 파일 목록. 루트 밖은 고를 수 없다."""

from pathlib import Path

PATTERNS = ("*.csv", "*.tsv", "*.txt")


def list_data_files(root: Path, patterns: tuple[str, ...] = PATTERNS) -> list[str]:
    """루트 기준 상대 경로(posix)를 정렬해 돌려준다. 숨김 디렉터리·파일은 건너뛴다."""
    root = root.resolve()
    found: set[str] = set()
    for pattern in patterns:
        for path in root.rglob(pattern):
            rel = path.relative_to(root)
            if any(part.startswith(".") for part in rel.parts) or not path.is_file():
                continue
            found.add(rel.as_posix())
    return sorted(found)


def resolve_within(root: Path, rel: str) -> Path:
    """rel 을 루트 기준으로 풀고, 심볼릭 링크를 따라간 결과가 루트 밖이면 ValueError."""
    root = root.resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"루트 밖의 경로입니다: {rel}")
    return path
