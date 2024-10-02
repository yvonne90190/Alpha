import os
import glob
import json
from enum import Enum
import alpha as alpha_lib

def load_pending_alphas():
    pending_path = alpha_lib.AlphaStage.PENDING.value
    json_files = glob.glob(os.path.join(pending_path, '*.json'))
    pending_alphas = []
    for file_path in json_files:
        alpha = alpha_lib.Alpha.read_from_disk(file_path)
        pending_alphas.append((alpha, file_path))
    return pending_alphas

