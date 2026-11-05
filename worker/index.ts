import handler from "vinext/server/fetch-handler";
import { runWithConnectorBinding } from "../lib/connector-context";
import type { ConnectorBinding } from "../lib/connector-contract.mjs";
import { createStudentAuth } from "../lib/student-auth";
import { privateAssetResponse,authorizeAssetPublisher } from "../lib/private-assets";

const worker = {
  async fetch(request: Request, env: Cloudflare.Env, ctx: ExecutionContext<{ CONNECTORS?: ConnectorBinding }>) {
    const publisher=await authorizeAssetPublisher(request,env);
    if(publisher)return (await privateAssetResponse(request,env,publisher))!;
    const access = await createStudentAuth(env).handle(request);
    if (access.response) return access.response;
    request = access.request!;
    const privateResponse=await privateAssetResponse(request,env);
    if(privateResponse)return privateResponse;
    let binding = ctx.props?.CONNECTORS;
    // Local preview emulates the same request-scoped capability. This branch and
    // the auxiliary service binding are absent from production builds.
    if (import.meta.env.DEV && !binding && env.CONNECTORS) {
      const preview = env.CONNECTORS;
      const expiresAt = Date.now() + 60_000;
      binding = {
        async getContext() {
          if (Date.now() >= expiresAt) return { status: "request_context_expired" };
          return preview.getContext?.() ?? { status: "binding_unavailable" };
        },
        async invoke(connectorId, actionName, args) {
          if (Date.now() >= expiresAt) {
            return { status: "request_context_expired", message: "This request has expired. Please try again." };
          }
          return preview.invoke(connectorId, actionName, args);
        },
      };
    }
    let response;
    if (env.ASSETS && ['GET','HEAD'].includes(request.method)) {
      const asset = await env.ASSETS.fetch(request);
      if (asset.status !== 404) response = asset;
    }
    response ??= await runWithConnectorBinding(binding, () => handler.fetch(request, env, ctx));
    const protectedResponse = new Response(response.body, response);
    protectedResponse.headers.set('Cache-Control', 'private, no-store');
    protectedResponse.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
    return protectedResponse;
  },
};

export default worker;
