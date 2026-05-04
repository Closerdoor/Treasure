PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS works (
  id TEXT PRIMARY KEY,
  module TEXT NOT NULL CHECK (module IN ('video', 'anime', 'book', 'music', 'game')),
  submodule TEXT CHECK (
    submodule IS NULL OR submodule IN (
      'movie',
      'tv_series',
      'documentary',
      'short_drama',
      'anime_movie',
      'anime_series'
    )
  ),
  schema_type TEXT NOT NULL CHECK (
    schema_type IN (
      'live_action_movie',
      'animated_movie',
      'live_action_series',
      'animated_series',
      'documentary_film',
      'documentary_series',
      'book',
      'music',
      'game'
    )
  ),
  title TEXT NOT NULL,
  original_title TEXT,
  year INTEGER,
  country TEXT,
  language TEXT,
  publish_company TEXT,
  runtime_minutes INTEGER,
  episode_count INTEGER,
  episode_runtime_minutes INTEGER,
  synopsis_text TEXT,
  synopsis_note TEXT,
  story_text TEXT,
  story_note TEXT,
  aliases_json TEXT,
  release_dates_json TEXT,
  identifiers_json TEXT,
  ratings_json TEXT,
  links_json TEXT,
  images_json TEXT,
  videos_json TEXT,
  reviews_json TEXT,
  soundtrack_json TEXT,
  relations_json TEXT,
  quotes_json TEXT,
  episode_stories_json TEXT,
  characters_json TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_works_module_submodule ON works (module, submodule);
CREATE INDEX IF NOT EXISTS idx_works_schema_type ON works (schema_type);
CREATE INDEX IF NOT EXISTS idx_works_status ON works (status);
CREATE INDEX IF NOT EXISTS idx_works_year ON works (year);

CREATE TABLE IF NOT EXISTS people (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  name_en TEXT,
  avatar_path TEXT,
  profile_link TEXT,
  notes TEXT,
  extra_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_people_name ON people (name, name_en);

CREATE TABLE IF NOT EXISTS work_credits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  work_id TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
  department TEXT NOT NULL CHECK (department IN ('direction', 'writing', 'cast', 'production', 'music', 'book', 'translation', 'original_work', 'other')),
  credit_type TEXT NOT NULL,
  display_label TEXT,
  character_name TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
  link_override TEXT,
  extra_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_work_credits_work_id ON work_credits (work_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_work_credits_person_id ON work_credits (person_id);

CREATE TABLE IF NOT EXISTS terms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  term_type TEXT NOT NULL CHECK (term_type IN ('genre', 'tag')),
  name TEXT NOT NULL,
  module_scope TEXT,
  submodule_scope TEXT,
  description TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_terms_scope ON terms (term_type, module_scope, submodule_scope, sort_order);
CREATE INDEX IF NOT EXISTS idx_terms_identity ON terms (term_type, name, module_scope, submodule_scope);

CREATE TABLE IF NOT EXISTS work_terms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  work_id TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
  term_id INTEGER NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  UNIQUE (work_id, term_id)
);

CREATE INDEX IF NOT EXISTS idx_work_terms_work_id ON work_terms (work_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_work_terms_term_id ON work_terms (term_id);

INSERT OR IGNORE INTO schema_migrations (version) VALUES ('0002_lite_schema');

COMMIT;
