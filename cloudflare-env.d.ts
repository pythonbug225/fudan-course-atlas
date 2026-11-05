declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
    BUCKET?: R2Bucket;
    REVIEW_ADMIN_EMAILS?: string;
    STUDENT_PASSWORD_PEPPER?: string;
    PRIVATE_ASSET_PUBLISH_KEY?: string;
    ASSETS?: { fetch(request:Request):Promise<Response> };
  }
}
