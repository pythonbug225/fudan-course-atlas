CREATE TABLE `private_asset_import_grants` (
	`token_hash` text PRIMARY KEY NOT NULL,
	`asset_version` text NOT NULL,
	`manifest_hash` text,
	`created_at` integer NOT NULL,
	`expires_at` integer NOT NULL,
	`revoked_at` integer
);
