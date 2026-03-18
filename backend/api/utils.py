import uuid

from api.constants import MAX_GENERATE_SHORT_CODE


def generate_short_code_from_id(pk):
    hex_dig = uuid.uuid4().hex
    return hex_dig[:MAX_GENERATE_SHORT_CODE]
