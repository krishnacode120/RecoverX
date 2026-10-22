import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";
export const authConfigured = !!(
  process.env.AUTH_SECRET &&
  process.env.AUTH_GITHUB_ID &&
  process.env.AUTH_GITHUB_SECRET
);
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: authConfigured ? [GitHub] : [],
  session: { strategy: "jwt", maxAge: 3600 },
  callbacks: {
    session({ session, token }) {
      if (session.user && token.sub) session.user.id = token.sub;
      return session;
    },
  },
});
