import { Suspense } from "react";
import type { Metadata } from "next";

import ForgotPasswordForm from "@/components/forgot-password-form";

export const metadata: Metadata = {
  title: "Recuperar contraseña | Nexova",
  description: "Solicita un enlace para restablecer tu contraseña en Nexova.",
};

export default function ForgotPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f6f7f2]" />}>
      <ForgotPasswordForm />
    </Suspense>
  );
}

