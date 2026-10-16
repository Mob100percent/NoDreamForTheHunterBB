# init_db.py
import sqlite3
import json

DB_PATH = "bloodborne.db"

# Fixed Dungeons data (scraped from thehuntersdream.com, deduplicated)
FIXED_DUNGEONS_JSON = """
[
  {
    "HolyGrailTypeId": 0,
    "RitualLevel": 1,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWgod3RcAAP////////////////////8+pk47WgAAAP////////////////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAtAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 1, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 0,
    "RitualLevel": 2,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWhQdQRgAAP////////////////////8+pk47WgAAAEimTjtbAAAA//////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 128, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 0,
    "RitualLevel": 3,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWh4dpRgAAKBHXzs9AAAAoOaDO1UAAAA+pk47WgAAAEimTjtbAAAA//////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 16384, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 0,
    "RitualLevel": 4,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWigdCRkAAEDOYDs+AAAAQANtO0YAAAA+pk47WgAAAEimTjtbAAAAXKZOO10AAACg3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 2097152, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 0,
    "RitualLevel": 5,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWjIdbRkAAEDOYDs+AAAA4POGO1cAAAA+pk47WgAAAEimTjtbAAAAXKZOO10AAACg3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAtAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 268435456, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 1,
    "RitualLevel": 2,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWhUdSxgAAP////////////////////+spk47XgAAAMB1ETsKAAAA//////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 256, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 1,
    "RitualLevel": 3,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWh8drxgAAP//////////QG2FO1YAAACspk47XgAAALamTjtfAAAAwHUROwoAAACg3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 32768, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 2,
    "RitualLevel": 4,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWiodHRkAAP////////////////////8kp047YAAAAP////////////////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 8388608, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 2,
    "RitualLevel": 5,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWjQdgRkAAP//////////gHqIO1gAAAAkp047YAAAAC6nTjthAAAA//////////+g3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 1073741824, 0],
    "WishMaterialList": []
  },
  {
    "HolyGrailTypeId": 3,
    "RitualLevel": 5,
    "SubFeatureFlag": 256,
    "FixedOrGeneral": 2,
    "FormData": "BQAAAIwAAAAAWjUdixkAAD6mTjtaAAAAIAGKO1kAAACSp047YgAAAEimTjtbAAAArKZOO14AAACg3UY7LQAAAP///////////////////////////////y0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "FormDataVersion": 0,
    "ShareLevel": 2,
    "Status": 1,
    "UnlockFlagList": [0, 2147483648, 0],
    "WishMaterialList": []
  }
]
"""


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # WAL mode: safe concurrent access (game server + webapp together).
    # journal_mode is persistent; busy_timeout makes writers queue instead
    # of failing when another writer holds the lock.
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")

    # --- Users ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_account_id TEXT UNIQUE NOT NULL,
            language_id INTEGER,
            region_id INTEGER,
            issuer_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --- Sessions ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # --- Characters (UNIQUE constraint removed on chara_id) ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chara_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # --- Blood Messages ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS blood_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blood_mess_id TEXT NOT NULL,
            area_id INTEGER,
            area_region_id INTEGER,
            channel_id INTEGER,
            blood_data TEXT,
            blood_data_version INTEGER,
            chara_data BOOLEAN,
            chara_data_version INTEGER,
            evaluate_minus INTEGER DEFAULT 0,
            evaluate_plus INTEGER DEFAULT 0,
            prev_blood_mess_id TEXT,
            user_id INTEGER,
            chara_id TEXT,
            mess_shell_info TEXT,
            mess_shell_info_version INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # --- Blood Message Evaluations ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS blood_message_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blood_mess_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            evaluate_kind INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(blood_mess_id) REFERENCES blood_messages(blood_mess_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            UNIQUE(blood_mess_id, user_id)
        )
    ''')

    # --- Tomb Messages ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS tomb_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tomb_mess_id TEXT NOT NULL,
            area_id INTEGER,
            area_region_id INTEGER,
            channel_id INTEGER,
            tomb_data TEXT,
            tomb_data_version INTEGER,
            death_vision_data TEXT,
            death_vision_data_version INTEGER,
            mess_shell_info TEXT,
            mess_shell_info_version INTEGER,
            user_id INTEGER,
            chara_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # --- Wandering Ghosts ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS wandering_ghosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wandering_ghost_id TEXT NOT NULL,
            area_id INTEGER,
            area_region_id INTEGER,
            channel_id INTEGER,
            chara_id TEXT,
            matching_level INTEGER,
            wandering_ghost_data TEXT,
            wandering_ghost_data_version INTEGER,
            user_id INTEGER,
            reject_ignore INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # --- Chair Messages ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS chair_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warp_info_id INTEGER,
            channel_id INTEGER,
            chara_id TEXT,
            user_id INTEGER,
            count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            UNIQUE(warp_info_id, channel_id, chara_id)
        )
    ''')

    # --- Chair Respawn Notices ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS chair_respawn_notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chara_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            channel_id INTEGER,
            warp_info_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # --- Channels (using id as ChannelId, no separate channel_id column) ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixed_or_general INTEGER,
            form_data TEXT,
            form_data_version INTEGER,
            holy_grail_type_id INTEGER,
            ritual_level INTEGER,
            status INTEGER DEFAULT 1,
            sub_feature_flag INTEGER DEFAULT 0,
            share_level INTEGER DEFAULT 0,
            turnout_level INTEGER DEFAULT 0,
            discernment_word TEXT,
            create_user_id INTEGER,
            create_chara_id TEXT,
            create_date TIMESTAMP,
            last_play_date TIMESTAMP,
            wish_material_list TEXT,
            spent_material_list TEXT,
            user_id INTEGER,
            chara_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Migration for DBs created before spent_material_list existed
    cols = [r[1] for r in c.execute("PRAGMA table_info(channels)").fetchall()]
    if "spent_material_list" not in cols:
        c.execute("ALTER TABLE channels ADD COLUMN spent_material_list TEXT")

    # --- Multi-play error reports (penalty bookkeeping) ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS multi_play_error_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            request_body TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS channel_unlock_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL,
            unlock_flag INTEGER,
            FOREIGN KEY(channel_id) REFERENCES channels(id)
        )
    ''')

    # --- Notices ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            is_emergency BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --- Messenger Shells ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS messenger_shells (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chara_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            shell_data TEXT,
            shell_data_version INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # --- Fixed Dungeons ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS fixed_dungeons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holy_grail_type_id INTEGER NOT NULL,
            ritual_level INTEGER NOT NULL,
            sub_feature_flag INTEGER NOT NULL,
            fixed_or_general INTEGER NOT NULL DEFAULT 2,
            form_data TEXT NOT NULL,
            form_data_version INTEGER NOT NULL,
            share_level INTEGER NOT NULL,
            status INTEGER NOT NULL,
            unlock_flag_list TEXT NOT NULL,
            wish_material_list TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(holy_grail_type_id, ritual_level, sub_feature_flag)
        )
    ''')

    # --- Insert default normal notice ---
    c.execute("SELECT COUNT(*) FROM notices")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO notices (title, content, is_emergency)
            VALUES (?, ?, ?)
        ''', (
            "VGhlIEh1bnRlcidzIERyZWFt",
            "V2VsY29tZSB0byB0aGUgcHJpdmF0ZSBCbG9vZGJvcm5lIHNlcnZlci4KCkZlYXIgdGhlIG9sZCBibG9vZC4=",
            0
        ))

    # --- Insert fixed dungeons ---
    data = json.loads(FIXED_DUNGEONS_JSON)
    inserted = 0
    for entry in data:
        unlock_flags_json = json.dumps(entry["UnlockFlagList"])
        wish_list_json = json.dumps(entry.get("WishMaterialList", []))
        c.execute('''
            INSERT OR IGNORE INTO fixed_dungeons (
                holy_grail_type_id, ritual_level, sub_feature_flag,
                fixed_or_general, form_data, form_data_version,
                share_level, status, unlock_flag_list, wish_material_list
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry["HolyGrailTypeId"],
            entry["RitualLevel"],
            entry["SubFeatureFlag"],
            entry["FixedOrGeneral"],
            entry["FormData"],
            entry["FormDataVersion"],
            entry["ShareLevel"],
            entry["Status"],
            unlock_flags_json,
            wish_list_json
        ))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Database initialised successfully. Inserted {inserted} fixed dungeons.")


if __name__ == "__main__":
    init_db()