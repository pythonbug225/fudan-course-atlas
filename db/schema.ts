// D1 tables used by the site.
import { sqliteTable, text, integer, index, uniqueIndex } from 'drizzle-orm/sqlite-core';
export const reviews = sqliteTable('community_reviews', {
 id: text('id').primaryKey(), courseId:text('course_id').notNull(), authorId:text('author_id').notNull(),
 teacher:text('teacher').notNull(), term:text('term').notNull(), classType:text('class_type').notNull(),
 nickname:text('nickname').notNull(), learning:text('learning').notNull(), workload:text('workload').notNull(),
 assessment:text('assessment').notNull(), grading:text('grading').notNull(), overall:text('overall').notNull(),
 grade:text('grade').notNull(), hours:integer('hours'), createdAt:text('created_at').notNull(),
 kind:text('kind').notNull().default('review'),
 status:text('status').notNull().default('legacy'),
 contentHash:text('content_hash'),moderatorId:text('moderator_id'),moderatedAt:text('moderated_at'),
 moderationNote:text('moderation_note').notNull().default(''),
}, t=>[index('reviews_course_date').on(t.courseId,t.createdAt),index('reviews_author_date').on(t.authorId,t.createdAt),index('reviews_status_date').on(t.status,t.createdAt),uniqueIndex('reviews_author_content').on(t.authorId,t.contentHash)]);
export const files=sqliteTable('review_files',{
 id:text('id').primaryKey(),reviewId:text('review_id').notNull(),objectKey:text('object_key').notNull(),
 name:text('name').notNull(),mime:text('mime').notNull(),size:integer('size').notNull()
},t=>[index('files_review').on(t.reviewId)]);

export const pointEvents=sqliteTable('point_events',{
 id:text('id').primaryKey(),userId:text('user_id').notNull(),
 eventType:text('event_type',{enum:['checkin','exam_unlock','submission_reward','submission_withdrawal']}).notNull(),
 eventKey:text('event_key').notNull(),delta:integer('delta').notNull(),createdAt:text('created_at').notNull(),
},t=>[
 uniqueIndex('point_events_user_event').on(t.userId,t.eventKey),
 index('point_events_user_created').on(t.userId,t.createdAt),
]);

export const compassProfiles = sqliteTable('compass_profiles', {
 userId: text('user_id').primaryKey(),
 activeSnapshotId: text('active_snapshot_id'),
 version: integer('version').notNull().default(0),
 updatedAt: text('updated_at').notNull(),
});

export const compassSnapshots = sqliteTable('compass_snapshots', {
 snapshotId: text('snapshot_id').primaryKey(),
 userId: text('user_id').notNull(),
 label: text('label').notNull(),
 stateJson: text('state_json').notNull(),
 version: integer('version').notNull().default(1),
 source: text('source').notNull(),
 importKey: text('import_key'),
 createdAt: text('created_at').notNull(),
 updatedAt: text('updated_at').notNull(),
}, t => [
 index('compass_snapshots_user_updated').on(t.userId, t.updatedAt),
 uniqueIndex('compass_snapshots_user_import').on(t.userId, t.importKey),
]);
