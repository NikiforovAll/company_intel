import "./globals.css";
import "@copilotkit/react-ui/v2/styles.css";
import type { ReactNode } from "react";
import { NavBar } from "./components/nav-bar";

export const metadata = {
  title: "Company Intel",
  description: "Company Intel Agent",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <NavBar />
        {children}
      </body>
    </html>
  );
}
