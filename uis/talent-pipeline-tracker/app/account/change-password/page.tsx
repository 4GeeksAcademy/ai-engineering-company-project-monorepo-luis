import type { Metadata } from "next";

import AccountChangePassword from "@/components/account-change-password";

export const metadata: Metadata = {
  title: "Cambiar contraseña | Nexova",
  description: "Actualiza tu contraseña de acceso a Nexova.",
};

export default function ChangePasswordPage() {
  return <AccountChangePassword />;
}

