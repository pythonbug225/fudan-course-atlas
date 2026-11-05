CREATE TABLE `compass_profiles` (
	`user_id` text PRIMARY KEY NOT NULL,
	`active_snapshot_id` text,
	`version` integer DEFAULT 0 NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `compass_snapshots` (
	`snapshot_id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`label` text NOT NULL,
	`state_json` text NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	`source` text NOT NULL,
	`import_key` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `compass_snapshots_user_updated` ON `compass_snapshots` (`user_id`,`updated_at`);--> statement-breakpoint
CREATE UNIQUE INDEX `compass_snapshots_user_import` ON `compass_snapshots` (`user_id`,`import_key`);