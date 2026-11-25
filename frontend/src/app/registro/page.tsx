import type { Metadata } from "next";
import { RegistroForm } from "@/components/AuthForm/RegistroForm";

export const metadata: Metadata = {
  title: "Crear cuenta · DiviEat",
};

export default function PaginaRegistro() {
  return <RegistroForm />;
}
