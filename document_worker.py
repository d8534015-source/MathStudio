"""Bounded PDF text extraction worker. The parent enforces the wall-clock deadline."""
import io
import sys
from dependency_check import require_distribution


def main():
    require_distribution('pypdf')
    from pypdf import PdfReader
    # Bound address space on platforms that support it. Windows relies on timeout
    # and input/output/page limits; a Windows Job Object memory cap is still pending.
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    except (ImportError,ValueError,OSError):
        pass
    data=sys.stdin.buffer.read(32*1024*1024+1)
    if len(data)>32*1024*1024: return 2
    reader=PdfReader(io.BytesIO(data))
    if reader.is_encrypted: return 2
    parts=[];length=0
    for page in reader.pages[:80]:
        text=(page.extract_text() or '')[:30000-length]
        parts.append(text);length+=len(text)
        if length>=30000:break
    sys.stdout.buffer.write('\n\n'.join(parts)[:30000].encode('utf-8'))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:raise SystemExit(2) from None
