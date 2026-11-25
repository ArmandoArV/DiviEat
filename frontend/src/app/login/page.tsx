import type { Metadata } from "next";
import { LoginForm } from "@/components/AuthForm/LoginForm";

export const metadata: Metadata = {
  title: "Iniciar sesión · DiviEat",
};

export default function PaginaLogin() {
  return <LoginForm />;
}
