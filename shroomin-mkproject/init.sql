CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  discord_id BIGINT NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE small_biomes (
  id SERIAL PRIMARY KEY,
  seed BIGINT NOT NULL,
  x INT NOT NULL,
  z INT NOT NULL,
  claimed_size INT NOT NULL,
  calculated_size INT,
  duplicate_seed_flag INT,
  manual_check_needed INT,
  user_id INT NOT NULL,
  created_at timestamptz NOT NULL default now(),
  min_x INT default NULL,
  min_z INT default NULL,
  max_x INT default NULL,
  max_z INT default NULL
);

CREATE TABLE large_biomes (
  id SERIAL PRIMARY KEY,
  seed BIGINT NOT NULL,
  x INT NOT NULL,
  z INT NOT NULL,
  claimed_size INT NOT NULL,
  calculated_size INT,
  duplicate_seed_flag INT,
  manual_check_needed INT,
  user_id INT NOT NULL,
  created_at timestamptz NOT NULL default now(),
  min_x INT default NULL,
  min_z INT default NULL,
  max_x INT default NULL,
  max_z INT default NULL
)