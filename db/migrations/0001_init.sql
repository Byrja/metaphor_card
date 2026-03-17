-- 0001_init.sql
-- Initial schema for metaphor_card MVP

CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  telegram_id BIGINT NOT NULL UNIQUE,
  username TEXT,
  display_name TEXT,
  locale TEXT DEFAULT 'ru',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE decks (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cards (
  id INTEGER PRIMARY KEY,
  deck_id INTEGER NOT NULL,
  code TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  image_uri TEXT NOT NULL,
  tags_json TEXT,
  intensity_level INTEGER DEFAULT 3,
  is_active BOOLEAN NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(deck_id) REFERENCES decks(id)
);

CREATE TABLE sessions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  scenario_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE session_messages (
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL,
  sender_role TEXT NOT NULL,
  message_text TEXT NOT NULL,
  stage_code TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE insights (
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  insight_text TEXT NOT NULL,
  small_step_text TEXT,
  emotion_tags_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(session_id) REFERENCES sessions(id),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE user_patterns (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  pattern_key TEXT NOT NULL,
  pattern_value TEXT,
  score REAL DEFAULT 0,
  last_seen_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE safety_events (
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  risk_level TEXT NOT NULL,
  trigger_source TEXT NOT NULL,
  trigger_payload_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(session_id) REFERENCES sessions(id),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX idx_sessions_user_started_at ON sessions(user_id, started_at DESC);
CREATE INDEX idx_session_messages_session_created_at ON session_messages(session_id, created_at);
CREATE INDEX idx_insights_user_created_at ON insights(user_id, created_at DESC);
CREATE INDEX idx_safety_events_user_created_at ON safety_events(user_id, created_at DESC);
CREATE INDEX idx_cards_deck_active ON cards(deck_id, is_active);
