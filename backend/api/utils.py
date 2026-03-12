import hashlib
from datetime import datetime

from api.constants import MAX_GENERATE_SHORT_CODE


def generate_short_code_from_id(pk):
    timestamp = str(datetime.now().timestamp()).encode()
    hash_input = (pk + timestamp.decode()).encode()
    hash_object = hashlib.md5(hash_input)
    hex_dig = hash_object.hexdigest()
    return hex_dig[:MAX_GENERATE_SHORT_CODE]
