export function isNexovaPublicPath(pathname: string): boolean {
  return (
    pathname === "/login" ||
    pathname === "/register" ||
    pathname === "/forgot-password" ||
    pathname === "/reset-password"
  );
}

export function isNexovaProtectedPath(pathname: string): boolean {
  return (
    pathname === "/" ||
    pathname.startsWith("/candidates/") ||
    pathname === "/account/profile" ||
    pathname === "/account/change-password"
  );
}