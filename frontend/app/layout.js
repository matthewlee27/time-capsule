import Header from "@/components/Header";
import "./globals.css";

export const metadata = {
  title: "Time Capsule",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Header />
        <main id="app">{children}</main>
      </body>
    </html>
  );
}
