import { Suspense } from "react";
import type { Metadata } from "next";

import ResetPasswordForm from "@/components/reset-password-form";

export const metadata: Metadata = {
  title: "Restablecer contraseña | Nexova",
  description: "Introduce tu nueva contraseña para tu cuenta de Nexova.",
  referrer: "no-referrer",
};

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f6f7f2]" />}>
      <ResetPasswordForm />
    </Suspense>
  );
}

