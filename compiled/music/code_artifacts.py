import subprocess, sys
from pathlib import Path
engine = Path(__file__).resolve().parents[2] / "pipeline.py"
if not engine.exists(): engine = Path('C:\\Users\\Huang\\Dropbox\\01 personal project\\Media Engagement\\AI video\\draft\\multimodal_research_prototype\\pipeline.py')
raise SystemExit(subprocess.call([sys.executable, str(engine), 'code', "--compiled", str(Path(__file__).parent)] + ['--source', 'artifact'] + sys.argv[1:]))
