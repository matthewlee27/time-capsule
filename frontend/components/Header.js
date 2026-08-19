"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Header() {
  const pathname = usePathname();

  return (
    <header>
      <h1>Time Capsule</h1>
      <nav>
        <Link href="/" className={pathname === "/" ? "active" : ""}>
          home
        </Link>
        <Link href="/calibrate" className={pathname === "/calibrate" ? "active" : ""}>
          calibrate
        </Link>
        <Link href="/analyze" className={pathname === "/analyze" ? "active" : ""}>
          analyze
        </Link>
      </nav>
    </header>
  );
}
