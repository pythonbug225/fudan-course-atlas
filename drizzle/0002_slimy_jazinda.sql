CREATE TABLE `point_events` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`event_type` text NOT NULL,
	`event_key` text NOT NULL,
	`delta` integer NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `point_events_user_event` ON `point_events` (`user_id`,`event_key`);--> statement-breakpoint
CREATE INDEX `point_events_user_created` ON `point_events` (`user_id`,`created_at`);