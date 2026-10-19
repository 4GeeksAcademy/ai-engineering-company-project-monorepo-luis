import { Suspense } from "react";
import AuthForm from "@/components/auth-form";

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f6f7f2]" />}>
      <AuthForm mode="register" />
    </Suspense>
  );
}