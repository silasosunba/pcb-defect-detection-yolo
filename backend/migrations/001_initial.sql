CREATE TABLE users (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('user','admin')) DEFAULT 'user',
 active BOOLEAN NOT NULL DEFAULT TRUE, created_at BIGINT NOT NULL, last_login BIGINT
);
CREATE TABLE sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at BIGINT NOT NULL
);
CREATE TABLE inspections (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), filename TEXT NOT NULL,
 created_at BIGINT NOT NULL, confidence DOUBLE PRECISION NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
 detections JSONB NOT NULL, duration_ms DOUBLE PRECISION NOT NULL, model_sha256 TEXT NOT NULL,
 sequence BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE
);
CREATE TABLE audit (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, actor_id TEXT REFERENCES users(id), action TEXT NOT NULL,
 target TEXT NOT NULL, created_at BIGINT NOT NULL
);
CREATE TABLE auth_attempts (ip TEXT NOT NULL, email TEXT NOT NULL, created_at BIGINT NOT NULL);
CREATE INDEX attempts_time ON auth_attempts(created_at);
CREATE INDEX attempts_ip ON auth_attempts(ip, created_at);
CREATE INDEX inspections_owner ON inspections(user_id, created_at, sequence);
CREATE INDEX session_expiry ON sessions(expires_at);
