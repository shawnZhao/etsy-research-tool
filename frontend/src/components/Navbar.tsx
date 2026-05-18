"use client";

import React from "react";
import Link from "next/link";
import { useTranslation } from "../lib/i18n/context";
import { LanguageSwitcher } from "./LanguageSwitcher";

export function Navbar() {
  const { t } = useTranslation();

  return (
    <nav className="bg-white border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-bold text-lg text-orange-600">
            {t("nav.brand")}
          </Link>
          <Link
            href="/keywords"
            className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            {t("nav.keywords")}
          </Link>
          <Link
            href="/shops"
            className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            {t("nav.competitors")}
          </Link>
          <Link
            href="/seo"
            className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            {t("nav.seoAudit")}
          </Link>
        </div>
        <LanguageSwitcher />
      </div>
    </nav>
  );
}
