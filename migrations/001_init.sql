-- SIRLI SAFAR — boshlang‘ich sxema (PostgreSQL / Supabase)

CREATE TABLE admins (
    tg_id               BIGINT PRIMARY KEY,
    name                TEXT,
    authenticated_until TIMESTAMPTZ,
    failed_attempts     INT NOT NULL DEFAULT 0,
    locked_until        TIMESTAMPTZ,
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE groups (
    chat_id    BIGINT PRIMARY KEY,
    title      TEXT NOT NULL,
    added_by   BIGINT,
    is_member  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Telegram foydalanuvchilari (asosiy identifikator — Telegram ID)
CREATE TABLE players (
    tg_id      BIGINT PRIMARY KEY,
    username   TEXT,
    full_name  TEXT NOT NULL,
    dm_ok      BOOLEAN NOT NULL DEFAULT FALSE,   -- botga shaxsiy /start bosganmi
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE stories (
    id        SERIAL PRIMARY KEY,
    slug      TEXT NOT NULL UNIQUE,
    title     TEXT NOT NULL,
    genre     TEXT NOT NULL DEFAULT '',
    synopsis  TEXT NOT NULL DEFAULT '',
    theme     INT NOT NULL DEFAULT 0,            -- zinapoya rasmi rang mavzusi
    position  INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE story_stages (
    id            SERIAL PRIMARY KEY,
    story_id      INT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    stage_no      INT NOT NULL CHECK (stage_no BETWEEN 1 AND 10),
    title         TEXT NOT NULL,
    body          TEXT NOT NULL,
    bridge        TEXT NOT NULL DEFAULT '',
    visual_desc   TEXT NOT NULL DEFAULT '',
    image_prompt  TEXT NOT NULL DEFAULT '',
    has_trap      BOOLEAN NOT NULL DEFAULT FALSE,
    final_scene   TEXT,
    media_file_id TEXT,
    media_type    TEXT CHECK (media_type IN ('photo', 'animation')),
    UNIQUE (story_id, stage_no)
);

CREATE TABLE tasks (
    id             SERIAL PRIMARY KEY,
    stage_no       INT NOT NULL CHECK (stage_no BETWEEN 1 AND 9),
    kind           TEXT NOT NULL CHECK (kind IN ('test', 'text', 'individual', 'creative')),
    question       TEXT NOT NULL,
    correct_option INT CHECK (correct_option BETWEEN 0 AND 3),
    time_limit_sec INT NOT NULL CHECK (time_limit_sec BETWEEN 10 AND 3600),
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    is_demo        BOOLEAN NOT NULL DEFAULT FALSE,
    created_by     BIGINT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tasks_stage ON tasks (stage_no) WHERE is_active;

CREATE TABLE task_options (
    id       SERIAL PRIMARY KEY,
    task_id  INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    position INT NOT NULL CHECK (position BETWEEN 0 AND 3),
    text     TEXT NOT NULL,
    UNIQUE (task_id, position)
);

-- Tayyor tuzoq topshiriqlari kutubxonasi
CREATE TABLE traps (
    id             SERIAL PRIMARY KEY,
    story_id       INT REFERENCES stories(id) ON DELETE CASCADE,  -- NULL = barcha hikoyalar
    stage_no       INT NOT NULL CHECK (stage_no BETWEEN 1 AND 9),
    prompt         TEXT NOT NULL,
    time_limit_sec INT NOT NULL CHECK (time_limit_sec BETWEEN 10 AND 3600),
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_by     BIGINT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_traps_stage ON traps (stage_no) WHERE is_active;

CREATE TABLE games (
    id                 SERIAL PRIMARY KEY,
    group_id           BIGINT NOT NULL REFERENCES groups(chat_id) ON UPDATE CASCADE,
    story_id           INT NOT NULL REFERENCES stories(id),
    admin_id           BIGINT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'lobby'
                       CHECK (status IN ('lobby', 'running', 'paused', 'finished', 'cancelled')),
    current_stage      INT NOT NULL DEFAULT 1 CHECK (current_stage BETWEEN 1 AND 10),
    max_stage_reached  INT NOT NULL DEFAULT 1,
    cleared_traps      INT[] NOT NULL DEFAULT '{}',
    lobby_message_id   BIGINT,
    lobby_dirty        BOOLEAN NOT NULL DEFAULT FALSE,
    last_individual_user BIGINT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at         TIMESTAMPTZ,
    paused_at          TIMESTAMPTZ,
    paused_total_sec   INT NOT NULL DEFAULT 0,
    finished_at        TIMESTAMPTZ
);
-- Bir guruhda bir vaqtda faqat bitta faol o‘yin
CREATE UNIQUE INDEX uq_games_one_active_per_group
    ON games (group_id) WHERE status IN ('lobby', 'running', 'paused');
CREATE INDEX idx_games_status ON games (status);

-- Har bir o‘yinning ro‘yxati (o‘yin boshlanganda muzlatiladi)
CREATE TABLE game_players (
    game_id         INT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_id         BIGINT NOT NULL REFERENCES players(tg_id),
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    times_selected  INT NOT NULL DEFAULT 0,
    PRIMARY KEY (game_id, user_id)
);

-- O‘yin davomida berilgan topshiriqlar (savol nusxasi saqlanadi)
CREATE TABLE game_tasks (
    id               BIGSERIAL PRIMARY KEY,
    game_id          INT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    seq              INT NOT NULL,
    stage_no         INT NOT NULL,
    kind             TEXT NOT NULL CHECK (kind IN ('test', 'text', 'individual', 'creative', 'trap')),
    task_id          INT REFERENCES tasks(id) ON DELETE SET NULL,
    trap_id          INT REFERENCES traps(id) ON DELETE SET NULL,
    question         TEXT NOT NULL DEFAULT '',
    options          JSONB,
    correct_option   INT,
    time_limit_sec   INT NOT NULL,
    assigned_user_id BIGINT REFERENCES players(tg_id),
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('needs_input', 'pending', 'open', 'awaiting_review',
                                       'resolved', 'skipped', 'cancelled')),
    outcome          TEXT CHECK (outcome IN ('correct', 'wrong', 'timeout')),
    deadline_at      TIMESTAMPTZ,
    warned           BOOLEAN NOT NULL DEFAULT FALSE,
    group_message_id BIGINT,
    dm_message_id    BIGINT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    opened_at        TIMESTAMPTZ,
    resolved_at      TIMESTAMPTZ,
    UNIQUE (game_id, seq)
);
CREATE INDEX idx_game_tasks_deadline ON game_tasks (deadline_at) WHERE status = 'open';
CREATE INDEX idx_game_tasks_game ON game_tasks (game_id, status);
-- Bir o‘yinda bir vaqtda faqat bitta faol topshiriq
CREATE UNIQUE INDEX uq_game_one_active_task ON game_tasks (game_id)
    WHERE status IN ('needs_input', 'pending', 'open', 'awaiting_review');
CREATE INDEX idx_game_tasks_group_msg ON game_tasks (group_message_id) WHERE group_message_id IS NOT NULL;

-- Har bir topshiriqqa FAQAT bitta yakuniy javob (UNIQUE)
CREATE TABLE answers (
    id           BIGSERIAL PRIMARY KEY,
    game_task_id BIGINT NOT NULL UNIQUE REFERENCES game_tasks(id) ON DELETE CASCADE,
    user_id      BIGINT NOT NULL REFERENCES players(tg_id),
    choice_index INT,
    text         TEXT,
    is_correct   BOOLEAN,
    graded_by    BIGINT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    graded_at    TIMESTAMPTZ
);
CREATE INDEX idx_answers_user ON answers (user_id);

CREATE TABLE game_events (
    id         BIGSERIAL PRIMARY KEY,
    game_id    INT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    type       TEXT NOT NULL,
    payload    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_game_events_game ON game_events (game_id, id);

CREATE TABLE results (
    game_id          INT PRIMARY KEY REFERENCES games(id) ON DELETE CASCADE,
    duration_sec     INT NOT NULL,
    total_tasks      INT NOT NULL,
    correct_count    INT NOT NULL,
    wrong_count      INT NOT NULL,
    timeout_count    INT NOT NULL,
    individual_done  INT NOT NULL,
    final_stage      INT NOT NULL,
    top_players      JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Global sozlamalar (kalit → qiymat)
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- aiogram FSM holati (server qayta ishga tushganda ham saqlanadi)
CREATE TABLE user_states (
    key        TEXT PRIMARY KEY,
    state      TEXT,
    data       JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
