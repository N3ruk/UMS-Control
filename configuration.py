# SPDX-License-Identifier: GPL-3.0-or-later
"""Non-destructive configuration loading and explicit recovery primitives."""
import json, os
from datetime import datetime, timezone
from pathlib import Path

class ConfigurationError(ValueError):
    def __init__(self,path,detail):
        self.path=Path(path)
        super().__init__(str(detail))

class StartupCancelled(Exception):
    pass

def read_object(path,default):
    path=Path(path)
    try:raw=path.read_text(encoding='utf-8')
    except FileNotFoundError:return default()
    except (OSError,UnicodeError) as error:raise ConfigurationError(path,str(error)) from error
    try:
        data=json.loads(raw)
        if not isinstance(data,dict):raise ValueError('Se esperaba un objeto JSON.')
        return data
    except (ValueError,UnicodeError) as error:raise ConfigurationError(path,str(error)) from error

def preserve(path):
    """Exclusive, private byte-for-byte copy; never rename or overwrite the input."""
    path=Path(path)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    target=path.with_name(path.name+'.recovery-'+stamp)
    raw=path.read_bytes()
    descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return target
