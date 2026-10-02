"""AppTest로 전 페이지를 헤드리스 실행해 예외를 잡는다."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1 import AppTest
from features import registry

ROOT = Path(__file__).resolve().parent.parent
fails = 0

for i, page in enumerate(registry.PAGES):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    at.run()
    if at.exception:
        print(f"[기동] 예외: {at.exception[0].message}")
        fails += 1
        break
    # 사이드바 라디오로 페이지 전환
    at.sidebar.radio[0].set_value(page.key).run()
    status = "OK"
    if at.exception:
        status = f"예외 {at.exception[0].value}"
        fails += 1
    err = [e.value for e in at.error]
    if err:
        status += f" | st.error: {err}"
    print(f"{page.icon} {page.label:<16} {status}"
          f"  (dataframe {len(at.dataframe)}, metric {len(at.metric)}, "
          f"warning {len(at.warning)})")

print("\n실패:", fails)
sys.exit(1 if fails else 0)
