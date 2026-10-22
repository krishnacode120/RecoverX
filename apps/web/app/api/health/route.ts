export function GET() {
  return Response.json({
    service: "recoverx-web",
    version: "0.1.0",
    status: "ok",
    diskAccess: false,
    uploads: false,
  });
}
