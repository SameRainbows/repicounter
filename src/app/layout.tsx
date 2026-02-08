import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "AI Workout Tracker",
  description: "Real-time rep counting and form feedback from your camera."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

