import { Suspense } from "react";
import AuthForm from "@/components/auth-form";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f6f7f2]" />}>
      <AuthForm mode="login" />
    </Suspense>
  );
}