-- Guruhdagi testlarda ko‘pchilik ovozi va o‘yin uchun hikoya rejimi (yoqilgan/o‘chirilgan)

ALTER TABLE games ADD COLUMN story_mode BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE game_tasks ADD COLUMN vote_dirty BOOLEAN NOT NULL DEFAULT FALSE;

-- Har bir o‘yinchi har bir testda FAQAT bitta ovoz beradi (PRIMARY KEY)
CREATE TABLE votes (
    game_task_id BIGINT NOT NULL REFERENCES game_tasks(id) ON DELETE CASCADE,
    user_id      BIGINT NOT NULL REFERENCES players(tg_id),
    choice_index INT NOT NULL CHECK (choice_index >= 0),
    voted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (game_task_id, user_id)
);
CREATE INDEX idx_votes_user ON votes (user_id);
