from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from tw_transcript_agent.env import load_env_file
from tw_transcript_agent.web import create_app

if __name__ == '__main__':
    load_env_file(Path(__file__).resolve().parent / '.env')
    create_app().run(host='127.0.0.1', port=8080, debug=False)
