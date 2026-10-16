import os

# Env overrides: DB_PATH, BB_ENC_MODE, BB_ENC_KEY_FILE.
DB_PATH = os.environ.get("DB_PATH", "bloodborne.db")
SS_INFO_FILE = "ss_info.xml"
US_SS_INFO_FILE = "us_ss_info.xml"
ASIA_SS_INFO_FILE = "asia_ss_info.xml"
SESSION_EXPIRY_HOURS = 24
# Env override: DEBUG=0 disables the debug_logger request/response logging.
DEBUG = os.environ.get("DEBUG", "1").lower() in ("1", "true", "yes")

# SENB body encryption (client <-> this server). Modes:
#   off       - no encryption (original behavior)
#   optional  - encrypted and plaintext requests both accepted
#   required  - request bodies must be SENB-encrypted (empty GET bodies pass)
# The key file holds the same PSK value as the shadNet 31313 key
# (client-side shadnet_key.txt); it is derived with domain separation, so it
# is never used raw. Keep this file secret and out of version control.
# Env overrides: BB_ENC_MODE, BB_ENC_KEY_FILE.
BB_ENC_MODE = os.environ.get("BB_ENC_MODE", "off")
BB_ENC_KEY_FILE = os.environ.get("BB_ENC_KEY_FILE", "bb_enc_key.txt")