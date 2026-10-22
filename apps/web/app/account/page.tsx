import Link from "next/link";
import { auth, authConfigured, signIn, signOut } from "@/lib/auth";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { CloudAccount } from "@/components/cloud-account";
export const dynamic = "force-dynamic";
export default async function Account() {
  const session = authConfigured ? await auth() : null;
  return (
    <>
      <header className="site-nav wrap">
        <Brand />
        <Link href="/dashboard">Back to workspace ↗</Link>
      </header>
      <main id="main" className="document">
        <div className="eyebrow">OPTIONAL CLOUD ACCOUNT</div>
        <h1>Your account. Your choice.</h1>
        <p>
          Local recovery and browser report viewing always work without an
          account. Sign in only to save private aggregate scan summaries.
        </p>
        {!authConfigured ? (
          <div className="note">
            <h3>Cloud account service is not configured</h3>
            <p>
              The deployment owner must configure GitHub OAuth, AUTH_SECRET and
              the PostgreSQL database. Local report viewing remains available.
            </p>
          </div>
        ) : session ? (
          <>
            <p>Signed in as {session.user?.name ?? "RecoverX user"}.</p>
            <CloudAccount />
            <form
              action={async () => {
                "use server";
                await signOut({ redirectTo: "/" });
              }}
            >
              <Button variant="outline">Sign out</Button>
            </form>
          </>
        ) : (
          <form
            action={async () => {
              "use server";
              await signIn("github", { redirectTo: "/account" });
            }}
          >
            <Button>Continue with GitHub</Button>
          </form>
        )}
      </main>
    </>
  );
}
