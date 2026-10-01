create table if not exists profiles (
  id uuid primary key,
  phone text unique not null,
  display_name text,
  language_preferences jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists translation_sessions (
  id uuid primary key,
  user_id uuid not null references profiles(id),
  source_language varchar(2) not null,
  target_language varchar(2) not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  ended_at timestamptz
);

create table if not exists translation_segments (
  id uuid primary key,
  session_id uuid not null references translation_sessions(id),
  source_text text not null,
  translated_text text not null,
  source_language varchar(2) not null,
  target_language varchar(2) not null,
  latency_ms integer not null,
  created_at timestamptz not null default now()
);
