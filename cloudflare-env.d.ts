declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
    BUCKET?: R2Bucket;
    REVIEW_ADMIN_EMAILS?: string;
  }
}
