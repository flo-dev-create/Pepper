ls transcribe_helper.py 2>/dev/null || cat << 'EOF' > transcribe_helper.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import whisper

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    
    audio_path = sys.argv[1]
    if not os.path.exists(audio_path):
        sys.exit(1)

    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="fr", fp16=False)
    print(result.get("text", "").strip())

if __name__ == "__main__":
    main()
EOF
chmod +x transcribe_helper.py
