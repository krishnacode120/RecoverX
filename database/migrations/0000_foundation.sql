CREATE TABLE users (id text PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE scan_sessions (
 id text PRIMARY KEY, user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 local_scan_id text NOT NULL, mode text NOT NULL CHECK(mode IN ('quick','deep')),
 status text NOT NULL CHECK(status IN ('running','complete','cancelled','failed')),
 total_bytes bigint NOT NULL CHECK(total_bytes >= 0), candidate_count integer NOT NULL CHECK(candidate_count >= 0),
 verified_count integer NOT NULL CHECK(verified_count >= 0), likely_count integer NOT NULL CHECK(likely_count >= 0),
 started_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(verified_count + likely_count <= candidate_count)
);
CREATE INDEX scans_user_created_idx ON scan_sessions(user_id, created_at);
-- Future agent pairing and recovery export metadata are distinct from scan candidates.
CREATE TABLE connected_agents (
 id text PRIMARY KEY, user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 agent_name text NOT NULL, agent_version text NOT NULL, last_seen timestamptz, revoked_at timestamptz
);
CREATE INDEX agents_user_idx ON connected_agents(user_id);
CREATE TABLE recovery_reports (
 id text PRIMARY KEY, scan_session_id text NOT NULL REFERENCES scan_sessions(id) ON DELETE CASCADE,
 attempted_count integer NOT NULL CHECK(attempted_count >= 0), success_count integer NOT NULL CHECK(success_count >= 0),
 partial_count integer NOT NULL CHECK(partial_count >= 0), failure_count integer NOT NULL CHECK(failure_count >= 0),
 created_at timestamptz NOT NULL DEFAULT now(), CHECK(attempted_count = success_count + partial_count + failure_count)
);
CREATE INDEX recovery_scan_idx ON recovery_reports(scan_session_id);
CREATE TABLE audit_events (
 id text PRIMARY KEY, user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 action text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_user_created_idx ON audit_events(user_id, created_at);
