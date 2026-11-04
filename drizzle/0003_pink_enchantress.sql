ALTER TABLE `community_reviews` ADD `status` text DEFAULT 'legacy' NOT NULL;--> statement-breakpoint
ALTER TABLE `community_reviews` ADD `content_hash` text;--> statement-breakpoint
ALTER TABLE `community_reviews` ADD `moderator_id` text;--> statement-breakpoint
ALTER TABLE `community_reviews` ADD `moderated_at` text;--> statement-breakpoint
ALTER TABLE `community_reviews` ADD `moderation_note` text DEFAULT '' NOT NULL;--> statement-breakpoint
CREATE INDEX `reviews_status_date` ON `community_reviews` (`status`,`created_at`);--> statement-breakpoint
CREATE UNIQUE INDEX `reviews_author_content` ON `community_reviews` (`author_id`,`content_hash`);