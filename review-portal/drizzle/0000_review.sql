CREATE TABLE workspaces (
  id TEXT PRIMARY KEY NOT NULL,
  session_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  state TEXT NOT NULL DEFAULT 'open',
  deadline INTEGER,
  completed_at INTEGER
);
--> statement-breakpoint
CREATE TABLE receipts (
  id TEXT PRIMARY KEY NOT NULL,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  idem TEXT NOT NULL,
  evidence TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  UNIQUE(workspace_id, idem)
);
--> statement-breakpoint
CREATE TABLE offers (
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  seat TEXT NOT NULL,
  fan TEXT NOT NULL,
  price INTEGER NOT NULL,
  PRIMARY KEY(workspace_id, seat),
  UNIQUE(workspace_id, fan)
);
