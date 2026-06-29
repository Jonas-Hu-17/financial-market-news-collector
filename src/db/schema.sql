-- ============ 摄取层 ============
CREATE TABLE IF NOT EXISTS source (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL,
  type         TEXT NOT NULL,              -- rss / edgar / hkex / api
  url          TEXT,
  trust_tier   INTEGER NOT NULL DEFAULT 2, -- 1 最权威 .. 3 一般
  language     TEXT,
  category     TEXT,
  enabled      INTEGER NOT NULL DEFAULT 1,
  fetch_config TEXT,                        -- JSON
  created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_item (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id     INTEGER REFERENCES source(id),
  external_id   TEXT,                       -- 源自带 guid
  url           TEXT,
  canonical_url TEXT,
  title         TEXT NOT NULL,
  summary       TEXT,
  author        TEXT,
  published_at  TEXT,
  fetched_at    TEXT NOT NULL,
  dedup_key     TEXT NOT NULL UNIQUE,       -- 规范URL+内容哈希，全局持久化
  content_hash  TEXT,
  language      TEXT,
  raw_payload   TEXT                        -- JSON 原始全量
);
CREATE INDEX IF NOT EXISTS idx_raw_item_published ON raw_item(published_at);
CREATE INDEX IF NOT EXISTS idx_raw_item_source ON raw_item(source_id);

-- ============ 加工层 ============
CREATE TABLE IF NOT EXISTS story (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  canonical_title   TEXT NOT NULL,
  dedup_cluster_key TEXT,
  first_seen_at     TEXT NOT NULL,
  last_seen_at      TEXT NOT NULL,
  last_update_at    TEXT,
  status            TEXT NOT NULL DEFAULT 'new'  -- new/ongoing/updated/dormant
);
CREATE INDEX IF NOT EXISTS idx_story_status ON story(status);
CREATE INDEX IF NOT EXISTS idx_story_last_seen ON story(last_seen_at);

CREATE TABLE IF NOT EXISTS story_member (
  story_id    INTEGER NOT NULL REFERENCES story(id) ON DELETE CASCADE,
  raw_item_id INTEGER NOT NULL REFERENCES raw_item(id) ON DELETE CASCADE,
  is_primary  INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (story_id, raw_item_id)
);
CREATE INDEX IF NOT EXISTS idx_story_member_raw ON story_member(raw_item_id);

CREATE TABLE IF NOT EXISTS score (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  story_id             INTEGER NOT NULL REFERENCES story(id) ON DELETE CASCADE,
  model                TEXT,
  score                REAL NOT NULL,        -- 0-10
  importance_rationale TEXT,
  scored_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_score_story ON score(story_id);

CREATE TABLE IF NOT EXISTS enrichment (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  story_id             INTEGER NOT NULL REFERENCES story(id) ON DELETE CASCADE,
  context_text         TEXT,
  corroborating_sources TEXT,                -- JSON
  confidence           TEXT,                 -- confirmed / unconfirmed
  created_at           TEXT NOT NULL
);

-- ============ 分类 / 实体 ============
CREATE TABLE IF NOT EXISTS taxonomy (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  dimension  TEXT NOT NULL,   -- market_type/industry_group/product_group/region/asset_class
  code       TEXT NOT NULL,
  label      TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  UNIQUE (dimension, code)
);

CREATE TABLE IF NOT EXISTS story_tag (
  story_id    INTEGER NOT NULL REFERENCES story(id) ON DELETE CASCADE,
  taxonomy_id INTEGER NOT NULL REFERENCES taxonomy(id) ON DELETE CASCADE,
  PRIMARY KEY (story_id, taxonomy_id)
);

CREATE TABLE IF NOT EXISTS entity (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  type        TEXT NOT NULL,   -- company/ticker/sector/person
  name        TEXT NOT NULL,
  ticker      TEXT,
  identifiers TEXT,            -- JSON: ISIN/CIK 等
  created_at  TEXT NOT NULL,
  UNIQUE (type, name)
);

CREATE TABLE IF NOT EXISTS story_entity (
  story_id  INTEGER NOT NULL REFERENCES story(id) ON DELETE CASCADE,
  entity_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  role      TEXT,              -- primary / related
  PRIMARY KEY (story_id, entity_id)
);

-- ============ 输出层 ============
CREATE TABLE IF NOT EXISTS brief (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  period_type      TEXT NOT NULL,   -- daily / 12h
  period_date      TEXT NOT NULL,
  language         TEXT NOT NULL DEFAULT 'zh',
  model            TEXT,
  generated_at     TEXT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'draft',
  market_view_text TEXT,            -- 整期综合市场观点
  UNIQUE (period_type, period_date, language)
);

CREATE TABLE IF NOT EXISTS brief_item (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  brief_id   INTEGER NOT NULL REFERENCES brief(id) ON DELETE CASCADE,
  story_id   INTEGER NOT NULL REFERENCES story(id) ON DELETE CASCADE,
  rank       INTEGER NOT NULL,
  headline   TEXT,
  summary    TEXT,
  view_text  TEXT,                  -- 单条中性影响陈述
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_brief_item_brief ON brief_item(brief_id);

-- ============ 产品层（Phase 2 预留，本阶段不写入） ============
CREATE TABLE IF NOT EXISTS app_user (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  email      TEXT UNIQUE,
  name       TEXT,
  plan       TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subscription (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER REFERENCES app_user(id) ON DELETE CASCADE,
  config      TEXT,   -- JSON: 订阅的 source/topic/阈值/渠道/语言
  created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS delivery (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id   INTEGER REFERENCES app_user(id) ON DELETE CASCADE,
  brief_id  INTEGER REFERENCES brief(id) ON DELETE CASCADE,
  channel   TEXT,
  sent_at   TEXT,
  status    TEXT
);
CREATE TABLE IF NOT EXISTS event (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER REFERENCES app_user(id) ON DELETE CASCADE,
  brief_item_id INTEGER REFERENCES brief_item(id) ON DELETE CASCADE,
  type          TEXT,   -- open / click / dwell
  ts            TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER REFERENCES app_user(id) ON DELETE CASCADE,
  brief_item_id INTEGER REFERENCES brief_item(id) ON DELETE CASCADE,
  rating        INTEGER,
  comment       TEXT,
  ts            TEXT
);

CREATE TABLE IF NOT EXISTS watchlist_item (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER,            -- Phase1 用固定默认用户 id=1（不强制外键）
  entity_id  INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  note       TEXT,
  added_at   TEXT NOT NULL,
  UNIQUE (user_id, entity_id)
);
