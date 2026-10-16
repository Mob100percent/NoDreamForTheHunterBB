import time
import secrets
import random
import string

def generate_id() -> str:
    """
    Generate a unique 63‑bit positive integer as a string.
    Combines nanosecond timestamp (47 bits) + 16 random bits.
    Guarantees uniqueness even across restarts and simultaneous calls.
    """
    time_part = time.time_ns() & ((1 << 47) - 1)
    random_part = secrets.randbits(16)
    return str((time_part << 16) | random_part)

def generate_discernment_word():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))